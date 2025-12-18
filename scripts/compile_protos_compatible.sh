#!/bin/bash
# Compile Protocol Buffer definitions with protobuf 5.x compatibility
# This ensures proto files work with grpcio-tools 1.62.0

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

echo -e "${GREEN}Compiling Protocol Buffers with protobuf 5.x compatibility...${NC}"
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

# Check current protobuf version
CURRENT_PROTOBUF=$(python3 -c "import google.protobuf; print(google.protobuf.__version__)" 2>/dev/null || echo "not installed")
echo -e "${YELLOW}Current protobuf version: ${CURRENT_PROTOBUF}${NC}"

# Check if we need to install/temporarily use protobuf 5.x
PROTOBUF_MAJOR=$(echo "${CURRENT_PROTOBUF}" | cut -d. -f1)
if [ "${PROTOBUF_MAJOR}" -ge 6 ]; then
    echo -e "${YELLOW}Warning: protobuf ${CURRENT_PROTOBUF} is installed (6.x).${NC}"
    echo -e "${YELLOW}We need protobuf 5.x for compatibility with grpcio-tools 1.62.0.${NC}"
    echo -e "${YELLOW}Installing protobuf 5.x temporarily in a virtual environment...${NC}"
    
    # Create a temporary virtual environment for compilation
    TEMP_VENV="${PROJECT_ROOT}/.proto_compile_venv"
    if [ ! -d "${TEMP_VENV}" ]; then
        python3 -m venv "${TEMP_VENV}"
    fi
    
    # Activate venv and install compatible versions
    source "${TEMP_VENV}/bin/activate"
    pip install --quiet --upgrade pip
    pip install --quiet "protobuf>=4.21.6,<5.0" "grpcio-tools==1.62.0"
    
    PYTHON_CMD="${TEMP_VENV}/bin/python"
    echo -e "${GREEN}Using temporary venv with protobuf 5.x${NC}"
else
    PYTHON_CMD="python3"
    echo -e "${GREEN}Using system Python with protobuf ${CURRENT_PROTOBUF}${NC}"
fi

# Verify protobuf version in the environment we'll use
VENV_PROTOBUF=$(${PYTHON_CMD} -c "import google.protobuf; print(google.protobuf.__version__)" 2>/dev/null || echo "unknown")
echo -e "${GREEN}Compiling with protobuf version: ${VENV_PROTOBUF}${NC}"

# Compile proto file
echo -e "${GREEN}Compiling ${PROTO_FILE}...${NC}"
${PYTHON_CMD} -m grpc_tools.protoc \
    --proto_path="${PROTO_DIR}" \
    --python_out="${OUTPUT_DIR}" \
    --grpc_python_out="${OUTPUT_DIR}" \
    "${PROTO_FILE}"

# Check if compilation was successful
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Successfully compiled proto files${NC}"
    
    # Fix import in generated grpc file (change absolute to relative import)
    GRPC_FILE="${OUTPUT_DIR}/cognitive_orch_pb2_grpc.py"
    if [ -f "${GRPC_FILE}" ]; then
        echo -e "${YELLOW}Fixing import in ${GRPC_FILE}...${NC}"
        # Replace absolute import with relative import
        sed -i.bak 's/^import cognitive_orch_pb2/from . import cognitive_orch_pb2/' "${GRPC_FILE}" 2>/dev/null || \
        sed -i '' 's/^import cognitive_orch_pb2/from . import cognitive_orch_pb2/' "${GRPC_FILE}" 2>/dev/null || \
        python3 -c "
import re
with open('${GRPC_FILE}', 'r') as f:
    content = f.read()
content = re.sub(r'^import cognitive_orch_pb2', 'from . import cognitive_orch_pb2', content, flags=re.MULTILINE)
with open('${GRPC_FILE}', 'w') as f:
    f.write(content)
"
        # Remove backup file if created
        [ -f "${GRPC_FILE}.bak" ] && rm "${GRPC_FILE}.bak"
        echo -e "${GREEN}✓ Fixed import statement${NC}"
    fi
    
    echo "Generated files in: ${OUTPUT_DIR}"
    ls -la "${OUTPUT_DIR}"
    
    # Verify the generated files don't have runtime_version import
    if grep -q "runtime_version" "${OUTPUT_DIR}/cognitive_orch_pb2.py" 2>/dev/null; then
        echo -e "${RED}✗ Warning: Generated files still contain runtime_version import${NC}"
        echo -e "${RED}  This suggests protobuf 6.x was used. Please check your environment.${NC}"
        exit 1
    else
        echo -e "${GREEN}✓ Generated files are compatible with protobuf 5.x${NC}"
    fi
else
    echo -e "${RED}✗ Proto compilation failed${NC}"
    exit 1
fi

# Deactivate venv if we used one
if [ -n "${VIRTUAL_ENV}" ] && [ "${VIRTUAL_ENV}" = "${TEMP_VENV}" ]; then
    deactivate
fi

echo -e "${GREEN}✓ Proto compilation completed successfully${NC}"

