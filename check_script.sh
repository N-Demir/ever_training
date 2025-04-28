#!/bin/bash

echo "Checking Node and Yarn versions..."
node -v
yarn -v

echo ""
echo "Checking if yarn.lock exists..."
if [ -f yarn.lock ]; then
  echo "✅ yarn.lock found"
else
  echo "❌ yarn.lock is missing!"
fi

echo ""
echo "Checking for global @types packages (via Yarn)..."
yarn global list | grep "@types" || echo "No global @types packages found."

echo ""
echo "Checking tsconfig.json settings..."
if [ -f tsconfig.json ]; then
  if grep -q '"typeRoots"' tsconfig.json; then
    echo "⚙️ typeRoots is defined in tsconfig.json"
  else
    echo "ℹ️ No typeRoots setting in tsconfig.json (defaults to ./node_modules/@types)"
  fi

  if grep -q '"types"' tsconfig.json; then
    echo "⚙️ Specific types are listed in tsconfig.json"
  else
    echo "ℹ️ No specific types listed — all installed types will be used"
  fi
else
  echo "❌ tsconfig.json is missing!"
fi

echo ""
echo "Checking installed @types packages locally..."
yarn list --pattern @types || echo "No @types packages found locally."

echo ""
echo "✅ Done checking!"