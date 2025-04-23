"""A simple example to render a (large-scale) Gaussian Splats

```bash
python examples/simple_viewer.py --scene_grid 13
```
"""

import argparse
from dataclasses import dataclass
import math
import os
import subprocess
import time

import imageio
from arguments import GroupParams, ModelParams, PipelineParams
import nerfview
import numpy as np
import torch
import torch.nn.functional as F
import tqdm

from scene.cameras import MiniCam
from scene.gaussian_model import GaussianModel
from utils.system_utils import searchForMaxIteration
from .read_write_model import read_images_binary

from gaussian_renderer.fast_renderer import FastRenderer
from gaussian_renderer.ever import splinerender

import viser
import viser.transforms as tf
renderFunc = splinerender


def get_gcloud_storage_list(gcs_path="gs://tour_storage/output"):
    try:
        # Run the gcloud command
        result = subprocess.run(
            ["gcloud", "storage", "ls", gcs_path],
            capture_output=True,
            text=True,
            check=True
        )
        # Split the output into a list of items
        items = result.stdout.strip().split('\n')

        # Results are sorted oldest to newest, so we reverse it
        items = items[::-1]

        # If the output ends in a /, remove it
        items = [item[:-1] if item.endswith('/') else item for item in items]

        # Outputs are `gs://tour_storage/output/120d7e96-2` so we take just the last part
        items = [item.split('/')[-1] for item in items]

        # Remove the / from the start of the items
        items = [item[1:] if item.startswith('/') else item for item in items]

        return items
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}")
        return []


@dataclass
class StartingCamera:
    translation: np.ndarray
    rotation: np.ndarray

# selected_3dgs: State3DGS | None = None
selected_3dgs: GaussianModel | None = None
starting_camera: StartingCamera | None = None


def main(dataset: ModelParams, pp: GroupParams, port: int = 8080):
    global selected_3dgs
    torch.manual_seed(42)
    device = torch.device("cuda", 0)
    server = viser.ViserServer(port=port, verbose=False)
    splat_select = server.gui.add_dropdown("3DGS", get_gcloud_storage_list())
    camera_select = server.gui.add_text("Camera from 'dataset/scene':", "youtube/75_first_ave")

    def on_select_camera(_):
        global starting_camera
        value = str(camera_select.value)

        selected_camera_select_path = f"gs://tour_storage/data/{value}/sparse_colmap/images.bin"

        subprocess.run(["gsutil", "cp", selected_camera_select_path, "images.bin"])
        images = read_images_binary("images.bin")
        # select the lexically first key in images
        first_image = images[1]
        rotation = first_image.qvec
        translation = first_image.tvec
        starting_camera = StartingCamera(translation, rotation)
    on_select_camera(None)
    camera_select.on_update(on_select_camera)

    def on_select_3dgs(_):
        global selected_3dgs
        global starting_camera
        value = splat_select.value

        # Download the checkpoint from GCS
        selected_3dgs_gcs_ckpts_path = f"gs://tour_storage/output/{value}/ckpts"

        ckpt_file_names = get_gcloud_storage_list(selected_3dgs_gcs_ckpts_path)
        selected_3dgs_gcs_path = f"{selected_3dgs_gcs_ckpts_path}/{ckpt_file_names[0]}"

        subprocess.run(["gsutil", "cp", selected_3dgs_gcs_path, "ckpt.pt"])
        
        selected_3dgs = GaussianModel(dataset.sh_degree, dataset.use_neural_network, dataset.max_opacity)

        loaded_iter = searchForMaxIteration(os.path.join(dataset.model_path, "point_cloud"))
        print("Loading trained model at iteration {}".format(loaded_iter))
        selected_3dgs.load_ply(os.path.join(dataset.model_path,
                                                       "point_cloud",
                                                       "iteration_" + str(loaded_iter),
                                                       "point_cloud.ply"))
        # splats = torch.load("ckpt.pt", map_location=device)["splats"]

        # sh0 = torch.cat([splats["sh0"]], dim=0)
        # shN = torch.cat([splats["shN"]], dim=0)
        # colors = torch.cat([sh0, shN], dim=-2)

        # selected_3dgs = State3DGS(
        #     selected_3dgs_name=value,
        #     means=torch.cat([splats["means"]], dim=0),
        #     quats=torch.cat([F.normalize(splats["quats"], p=2, dim=-1)], dim=0),
        #     scales=torch.cat([torch.exp(splats["scales"])], dim=0),
        #     opacities=torch.cat([torch.sigmoid(splats["opacities"])]),
        #     sh0=sh0,
        #     shN=shN,
        #     colors=colors,
        #     sh_degree=int(math.sqrt(colors.shape[-2]) - 1),
        # )
        # print("Number of Gaussians:", len(selected_3dgs.means))
    # Run it once to initialize the value
    on_select_3dgs(None)
    # Then register the callback
    splat_select.on_update(on_select_3dgs)
    starting_wxyz = starting_camera.rotation
    starting_position = starting_camera.translation


    @server.on_client_connect
    def _(client: viser.ClientHandle) -> None:
        """For each client that connects, we create a set of random frames + a click handler for each frame.

        When a frame is clicked, we move the camera to the corresponding frame.
        """
        reset_camera_button = server.gui.add_button("Reset Camera")

        def reset_camera(_):
            T_world_current = tf.SE3.from_rotation_and_translation(
                tf.SO3(client.camera.wxyz), client.camera.position
            )
            T_world_target = tf.SE3.from_rotation_and_translation(
                tf.SO3(starting_wxyz), starting_position
            ) @ tf.SE3.from_translation(starting_position + np.array([0.1, 0.0, 0.0]))

            T_current_target = T_world_current.inverse() @ T_world_target

            for j in range(20):
                T_world_set = T_world_current @ tf.SE3.exp(
                    T_current_target.log() * j / 19.0
                )

                # We can atomically set the orientation and the position of the camera
                # together to prevent jitter that might happen if one was set before the
                # other.
                with client.atomic():
                    client.camera.wxyz = T_world_set.rotation().wxyz
                    client.camera.position = T_world_set.translation()

                client.flush()  # Optional!
                time.sleep(1.0 / 60.0)

            # Mouse interactions should orbit around the frame origin.
            client.camera.look_at = starting_position

        reset_camera_button.on_click(reset_camera)


    # register and open viewer
    @torch.no_grad()
    def viewer_render_fn(camera_state: nerfview.CameraState, img_wh: tuple[int, int]):
        global selected_3dgs
        width, height = img_wh
        c2w = camera_state.c2w
        K = camera_state.get_K(img_wh)
        c2w = torch.from_numpy(c2w).float().to(device)
        K = torch.from_numpy(K).float().to(device)
        viewmat = c2w.inverse()

        if selected_3dgs is None:
            return np.zeros((height, width, 3))
        
        view = MiniCam(width, height, camera_state.fov, camera_state.fov, 0.001, 100.0, viewmat[None], K[None])

        net_image = renderFunc(
            view,
            selected_3dgs,
            pp,
            torch.tensor([1, 1, 1], dtype=torch.float32, device="cuda"),
        )["render"]
        return net_image

    _ = nerfview.Viewer(
        server=server,
        render_fn=viewer_render_fn,
        mode="rendering",
    )

    print("Viewer running... Ctrl+C to exit.")
    time.sleep(100000)


if __name__ == "__main__":
    """
    # Use single GPU to view the scene
    CUDA_VISIBLE_DEVICES=0 python simple_viewer.py \
        --ckpt results/garden/ckpts/ckpt_3499_rank0.pt \
        --port 8081
    """
    parser = argparse.ArgumentParser()
    dataset = ModelParams(parser)
    pp = PipelineParams(parser)
    parser.add_argument("--output_dir", type=str, default="results/", help="where to dump outputs")
    parser.add_argument("--scene_grid", type=int, default=1, help="repeat the scene into a grid of NxN")
    # parser.add_argument("--ckpt", type=str, default=None, help="path to the .pt file")
    parser.add_argument("--port", type=int, default=8080, help="port for the viewer server")
    args = parser.parse_args()
    assert args.scene_grid % 2 == 1, "scene_grid must be odd"

    # cli(main, args, verbose=True)
    main(dataset.extract(args), pp.extract(args), args.port)

