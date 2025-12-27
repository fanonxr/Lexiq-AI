#!/bin/bash
# Compile Protocol Buffer definitions to Python stubs

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the project root directory (parent of scripts/)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROTO_DIR="${PROJECT_ROOT}/libs/proto"
OUTPUT_DIR="${PROJECT_ROOT}/apps/cognitive-orch/src/cognitive_orch/grpc/proto"

echo -e "${GREEN}Compiling Protocol Buffers...${NC}"
echo "Proto directory: ${PROTO_DIR}"
echo "Output directory: ${OUTPUT_DIR}"

# Check if proto directory exists
if [ ! -d "${PROTO_DIR}" ]; then
    echo -e "${RED}Error: Proto directory not found: ${PROTO_DIR}${NC}"
    exit 1
fi

# Check if proto file exists
PROTO_FILE="${PROTO_DIR}/cognitive_orch.proto"
if [ ! -f "${PROTO_FILE}" ]; then
    echo -e "${RED}Error: Proto file not found: ${PROTO_FILE}${NC}"
    exit 1
fi

# Create output directory if it doesn't exist
mkdir -p "${OUTPUT_DIR}"

# Check if grpc_tools.protoc is available
if ! python -m grpc_tools.protoc --version > /dev/null 2>&1; then
    echo -e "${YELLOW}Warning: grpc_tools.protoc not found. Installing grpcio-tools...${NC}"
    pip install grpcio-tools==1.62.0
fi

# Verify protobuf version compatibility
PROTOBUF_VERSION=$(python -c "import google.protobuf; print(google.protobuf.__version__)" 2>/dev/null || echo "unknown")
echo -e "${GREEN}Using protobuf version: ${PROTOBUF_VERSION}${NC}"
echo -e "${YELLOW}Note: Proto files must be compiled with protobuf version compatible with grpcio-tools 1.62.0 (protobuf < 5.0)${NC}"

# Compile proto file
echo -e "${GREEN}Compiling ${PROTO_FILE}...${NC}"
python -m grpc_tools.protoc \
    --proto_path="${PROTO_DIR}" \
    --python_out="${OUTPUT_DIR}" \
    --grpc_python_out="${OUTPUT_DIR}" \
    "${PROTO_FILE}"

# Check if compilation was successful
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Successfully compiled proto files${NC}"
    echo "Generated files in: ${OUTPUT_DIR}"
    ls -la "${OUTPUT_DIR}"
else
    echo -e "${RED}✗ Proto compilation failed${NC}"
    exit 1
fi

