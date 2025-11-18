#!/bin/bash
# MassGen Skills Installation Script
# Installs openskills CLI, Anthropic skills collection, and Crawl4AI skill

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Directories
AGENT_DIR=".agent"
SKILLS_DIR="${AGENT_DIR}/skills"
CRAWL4AI_SKILL_DIR="${SKILLS_DIR}/crawl4ai"

# Show help
show_help() {
    echo "MassGen Skills Installation Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help          Show this help message"
    echo "  --skip-openskills   Skip openskills CLI installation"
    echo "  --skip-anthropic    Skip Anthropic skills installation"
    echo "  --skip-crawl4ai     Skip Crawl4AI skill download"
    echo ""
    echo "This script installs:"
    echo "  1. openskills CLI (npm global package)"
    echo "  2. Anthropic skills collection (via openskills)"
    echo "  3. Crawl4AI skill (from docs.crawl4ai.com)"
    echo ""
    echo "All installations are idempotent - safe to run multiple times."
    exit 0
}

# Parse arguments
SKIP_OPENSKILLS=false
SKIP_ANTHROPIC=false
SKIP_CRAWL4AI=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            ;;
        --skip-openskills)
            SKIP_OPENSKILLS=true
            shift
            ;;
        --skip-anthropic)
            SKIP_ANTHROPIC=true
            shift
            ;;
        --skip-crawl4ai)
            SKIP_CRAWL4AI=true
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   MassGen Skills Installation${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

# Check npm
if ! command -v npm &> /dev/null; then
    echo -e "${RED}✗ Error: npm is not installed${NC}"
    echo -e "${YELLOW}Please install Node.js and npm first:${NC}"
    echo "  macOS:  brew install node"
    echo "  Linux:  sudo apt-get install nodejs npm"
    echo ""
    exit 1
fi

echo -e "${GREEN}✓ npm found: $(npm --version)${NC}"
echo ""

# 1. Install openskills CLI
if [ "$SKIP_OPENSKILLS" = false ]; then
    echo -e "${BLUE}[1/3] Installing openskills CLI...${NC}"

    if command -v openskills &> /dev/null; then
        echo -e "${YELLOW}⊙ openskills already installed: $(openskills --version 2>&1 | head -n1 || echo 'version check failed')${NC}"
    else
        echo "Installing openskills globally..."
        npm install -g openskills
        echo -e "${GREEN}✓ openskills installed successfully${NC}"
    fi
    echo ""
else
    echo -e "${YELLOW}⊙ Skipping openskills CLI installation${NC}"
    echo ""
fi

# 2. Install Anthropic skills collection
if [ "$SKIP_ANTHROPIC" = false ]; then
    echo -e "${BLUE}[2/3] Installing Anthropic skills collection...${NC}"

    # Check if openskills is available
    if ! command -v openskills &> /dev/null; then
        echo -e "${RED}✗ Error: openskills not found${NC}"
        echo "Run without --skip-openskills or install manually: npm install -g openskills"
        exit 1
    fi

    # Check if skills directory exists and has content
    if [ -d "$SKILLS_DIR" ] && [ "$(ls -A $SKILLS_DIR 2>/dev/null)" ]; then
        SKILL_COUNT=$(find "$SKILLS_DIR" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')
        echo -e "${YELLOW}⊙ Skills directory exists with ${SKILL_COUNT} skills${NC}"
        echo "Installing/updating Anthropic skills..."
        openskills install anthropics/skills --universal -y
        echo -e "${GREEN}✓ Anthropic skills updated${NC}"
    else
        echo "Installing Anthropic skills (first time)..."
        mkdir -p "$AGENT_DIR"
        openskills install anthropics/skills --universal -y
        echo -e "${GREEN}✓ Anthropic skills installed successfully${NC}"
    fi

    # Show installed skills
    if [ -d "$SKILLS_DIR" ]; then
        SKILL_COUNT=$(find "$SKILLS_DIR" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')
        echo -e "${GREEN}  Installed skills: ${SKILL_COUNT}${NC}"
    fi
    echo ""
else
    echo -e "${YELLOW}⊙ Skipping Anthropic skills installation${NC}"
    echo ""
fi

# 3. Download and install Crawl4AI skill
if [ "$SKIP_CRAWL4AI" = false ]; then
    echo -e "${BLUE}[3/3] Installing Crawl4AI skill...${NC}"

    if [ -d "$CRAWL4AI_SKILL_DIR" ]; then
        echo -e "${YELLOW}⊙ Crawl4AI skill directory already exists${NC}"
        echo -e "${YELLOW}  Skipping download (delete $CRAWL4AI_SKILL_DIR to reinstall)${NC}"
    else
        echo "Downloading Crawl4AI skill..."

        # Create temp directory
        TEMP_DIR=$(mktemp -d)
        trap "rm -rf $TEMP_DIR" EXIT

        # Download skill
        if curl -L -f -o "$TEMP_DIR/crawl4ai-skill.zip" https://docs.crawl4ai.com/assets/crawl4ai-skill.zip; then
            echo "Extracting to $CRAWL4AI_SKILL_DIR..."
            mkdir -p "$SKILLS_DIR"

            # Extract zip
            if command -v unzip &> /dev/null; then
                unzip -q "$TEMP_DIR/crawl4ai-skill.zip" -d "$TEMP_DIR"
            else
                echo -e "${YELLOW}⚠ unzip not found, trying tar...${NC}"
                tar -xzf "$TEMP_DIR/crawl4ai-skill.zip" -C "$TEMP_DIR" 2>/dev/null || {
                    echo -e "${RED}✗ Error: Cannot extract zip file (no unzip or tar)${NC}"
                    exit 1
                }
            fi

            # Move extracted content (handle different zip structures)
            if [ -d "$TEMP_DIR/crawl4ai" ]; then
                mv "$TEMP_DIR/crawl4ai" "$CRAWL4AI_SKILL_DIR"
            elif [ -d "$TEMP_DIR/crawl4ai-skill" ]; then
                mv "$TEMP_DIR/crawl4ai-skill" "$CRAWL4AI_SKILL_DIR"
            else
                # If zip extracts to multiple files, move them all
                mkdir -p "$CRAWL4AI_SKILL_DIR"
                mv "$TEMP_DIR"/* "$CRAWL4AI_SKILL_DIR/" 2>/dev/null || true
            fi

            echo -e "${GREEN}✓ Crawl4AI skill installed successfully${NC}"
        else
            echo -e "${RED}✗ Error: Failed to download Crawl4AI skill${NC}"
            echo -e "${YELLOW}  URL: https://docs.crawl4ai.com/assets/crawl4ai-skill.zip${NC}"
            echo -e "${YELLOW}  You can download and extract manually to: $CRAWL4AI_SKILL_DIR${NC}"
        fi
    fi
    echo ""
else
    echo -e "${YELLOW}⊙ Skipping Crawl4AI skill installation${NC}"
    echo ""
fi

# Summary
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Skills installation complete!${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

if [ -d "$SKILLS_DIR" ]; then
    TOTAL_SKILLS=$(find "$SKILLS_DIR" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')
    echo -e "${GREEN}Total skills available: ${TOTAL_SKILLS}${NC}"
    echo -e "${BLUE}Skills directory: ${SKILLS_DIR}${NC}"
    echo ""
fi

echo -e "${BLUE}Next steps:${NC}"
echo "  • Skills are now available in Claude Code and Gemini CLI"
echo "  • Run './scripts/init.sh' for full MassGen setup"
echo "  • See documentation: https://docs.massgen.ai"
echo ""
