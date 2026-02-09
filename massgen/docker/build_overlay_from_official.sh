#!/bin/bash
# Build script for MassGen overlay images from official GHCR runtimes.

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Defaults
TAG="latest"
BUILD_SUDO=false
BASE_IMAGE_STANDARD="ghcr.io/massgen/mcp-runtime:latest"
BASE_IMAGE_SUDO="ghcr.io/massgen/mcp-runtime-sudo:latest"
IMAGE_NAME="massgen/mcp-runtime-agent-browser"
DOCKERFILE="massgen/docker/Dockerfile.overlay"

while [[ $# -gt 0 ]]; do
    case "$1" in
        -t|--tag)
            TAG="$2"
            shift 2
            ;;
        -n|--name)
            IMAGE_NAME="$2"
            shift 2
            ;;
        --base-image)
            BASE_IMAGE_STANDARD="$2"
            shift 2
            ;;
        --base-image-sudo)
            BASE_IMAGE_SUDO="$2"
            shift 2
            ;;
        --sudo)
            BUILD_SUDO=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -t, --tag TAG             Image tag (default: latest)"
            echo "  -n, --name NAME           Output image name"
            echo "  --base-image IMAGE        Base image for standard build (default: ${BASE_IMAGE_STANDARD})"
            echo "  --base-image-sudo IMAGE   Base image for sudo build (default: ${BASE_IMAGE_SUDO})"
            echo "  --sudo                    Build sudo overlay variant"
            echo "  -h, --help                Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0"
            echo "  $0 --sudo"
            echo "  $0 -n my-runtime -t dev"
            echo "  $0 --base-image ghcr.io/massgen/mcp-runtime:v0.1.40"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use -h or --help for usage information."
            exit 1
            ;;
    esac
done

if [ "$BUILD_SUDO" = true ]; then
    if [ "$IMAGE_NAME" = "massgen/mcp-runtime-agent-browser" ]; then
        IMAGE_NAME="massgen/mcp-runtime-sudo-agent-browser"
    fi
    DOCKERFILE="massgen/docker/Dockerfile.overlay.sudo"
    BASE_IMAGE="$BASE_IMAGE_SUDO"
    echo -e "${BLUE}ℹ️  Building sudo overlay variant${NC}"
else
    BASE_IMAGE="$BASE_IMAGE_STANDARD"
fi

if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed or not in PATH${NC}"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo -e "${RED}Error: Docker daemon is not running${NC}"
    exit 1
fi

echo -e "${BLUE}Building MassGen overlay image from official runtime...${NC}"
echo -e "${BLUE}Output image: ${IMAGE_NAME}:${TAG}${NC}"
echo -e "${BLUE}Base image:   ${BASE_IMAGE}${NC}"
echo -e "${BLUE}Dockerfile:   ${DOCKERFILE}${NC}"
echo ""

docker build \
    --build-arg "BASE_IMAGE=${BASE_IMAGE}" \
    -t "${IMAGE_NAME}:${TAG}" \
    -f "${DOCKERFILE}" \
    .

echo ""
echo -e "${GREEN}✓ Build successful${NC}"
docker images "${IMAGE_NAME}:${TAG}" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
echo ""
echo -e "${BLUE}Use in config:${NC}"
echo -e "  command_line_execution_mode: \"docker\""
echo -e "  command_line_docker_image: \"${IMAGE_NAME}:${TAG}\""
if [ "$BUILD_SUDO" = true ]; then
    echo -e "  command_line_docker_enable_sudo: true"
fi
