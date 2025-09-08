#!/bin/bash
# Pipeline & Peril - Comprehensive Project Setup Script
# This script initializes the complete development environment

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

check_command() {
    if command -v "$1" &> /dev/null; then
        log_success "$1 is installed"
        return 0
    else
        log_error "$1 is not installed"
        return 1
    fi
}

create_directory() {
    if [ ! -d "$1" ]; then
        mkdir -p "$1"
        log_success "Created $1"
    else
        log_info "$1 already exists"
    fi
}

# Header
echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${PURPLE}                        Pipeline & Peril - Project Setup                          ${NC}"
echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Step 1: Check dependencies
log_info "Checking required dependencies..."
echo ""

MISSING_DEPS=0

# Check core tools
for cmd in git python3 make; do
    check_command "$cmd" || MISSING_DEPS=$((MISSING_DEPS + 1))
done

# Check optional but recommended tools
log_info ""
log_info "Checking optional tools..."
for cmd in uv tmux emacs node npm; do
    check_command "$cmd" || log_warning "$cmd is recommended but not required"
done

if [ $MISSING_DEPS -gt 0 ]; then
    log_error "Missing required dependencies. Please install them first."
    exit 1
fi

echo ""

# Step 2: Create directory structure
log_info "Creating project directory structure..."
echo ""

# Core directories
create_directory "docs"
create_directory "src/pipeline_and_peril"
create_directory "tests"
create_directory "scripts"

# Asset directories
create_directory "assets/tiles"
create_directory "assets/cards"
create_directory "assets/boards"
create_directory "assets/icons"

# Experiment directories
create_directory "experiments/001-dice-mechanics/data"
create_directory "experiments/001-dice-mechanics/analysis"
create_directory "experiments/001-dice-mechanics/artifacts"
create_directory "experiments/002-service-states/data"
create_directory "experiments/002-service-states/analysis"
create_directory "experiments/002-service-states/artifacts"
create_directory "experiments/003-cascade-failures/data"
create_directory "experiments/003-cascade-failures/analysis"
create_directory "experiments/003-cascade-failures/artifacts"

# Agent directories
create_directory "agents"

# Playtesting directories
create_directory "playtesting/sessions"
create_directory "playtesting/feedback"
create_directory "playtesting/photos"

# Build directories
create_directory "build"
create_directory "dist"

echo ""

# Step 3: Create placeholder files
log_info "Creating placeholder files..."
echo ""

# Create placeholder assets if they don't exist
[ ! -f "assets/tiles/service-tiles.svg" ] && touch "assets/tiles/service-tiles.svg" && log_success "Created service-tiles.svg"
[ ! -f "assets/cards/event-cards.svg" ] && touch "assets/cards/event-cards.svg" && log_success "Created event-cards.svg"
[ ! -f "playtesting/sessions/.gitkeep" ] && touch "playtesting/sessions/.gitkeep" && log_success "Created session placeholder"

echo ""

# Step 4: Python environment setup
if command -v uv &> /dev/null; then
    log_info "Setting up Python environment with uv..."
    echo ""
    
    if [ ! -d ".venv" ]; then
        uv venv
        log_success "Created virtual environment"
    else
        log_info "Virtual environment already exists"
    fi
    
    if [ -f "pyproject.toml" ]; then
        uv pip install -e .
        log_success "Installed project in development mode"
        
        # Install dev dependencies if available
        uv pip install -e ".[dev]" 2>/dev/null && log_success "Installed development dependencies" || log_info "No dev dependencies defined"
    fi
else
    log_warning "uv not found. Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh"
fi

echo ""

# Step 5: TMux sessions setup
if command -v tmux &> /dev/null; then
    log_info "Setting up TMux sessions..."
    echo ""
    
    for session in worker1 worker2 coordinator meta-coordinator; do
        if tmux has-session -t "$session" 2>/dev/null; then
            log_info "Session $session already exists"
        else
            tmux new-session -d -s "$session" -c "$PROJECT_ROOT"
            log_success "Created tmux session: $session"
        fi
    done
    
    echo ""
    log_info "TMux sessions status:"
    tmux list-sessions 2>/dev/null | sed 's/^/  /'
else
    log_warning "tmux not found. Parallel development sessions not created."
fi

echo ""

# Step 6: Git setup
log_info "Checking Git configuration..."
echo ""

if [ -d ".git" ]; then
    log_success "Git repository initialized"
    
    # Check for git notes
    if git notes list &>/dev/null; then
        log_success "Git notes configured"
    else
        log_info "Git notes not yet used"
    fi
    
    # Show current branch and status
    BRANCH=$(git branch --show-current)
    log_info "Current branch: $BRANCH"
    
    # Check for uncommitted changes
    if git diff-index --quiet HEAD -- 2>/dev/null; then
        log_success "Working directory clean"
    else
        log_warning "Uncommitted changes detected"
    fi
else
    log_error "Not a git repository. Run: git init"
fi

echo ""

# Step 7: Documentation check
log_info "Checking documentation..."
echo ""

for doc in README.org PROJECT-PLAN.org METHODOLOGY.org TODO.org; do
    if [ -f "$doc" ]; then
        log_success "$doc exists"
    else
        log_warning "$doc not found"
    fi
done

echo ""

# Step 8: Generate README.md if Emacs is available
if command -v emacs &> /dev/null && [ -f "README.org" ]; then
    log_info "Generating README.md from README.org..."
    if make README.md &>/dev/null; then
        log_success "README.md generated"
    else
        log_warning "Could not generate README.md"
    fi
else
    log_info "Emacs not found, skipping README.md generation"
fi

echo ""

# Step 9: Run tests if available
if [ -d "tests" ] && [ -n "$(ls -A tests/*.py 2>/dev/null)" ]; then
    log_info "Running tests..."
    if command -v uv &> /dev/null; then
        if uv run pytest tests/ -q; then
            log_success "All tests passed"
        else
            log_warning "Some tests failed"
        fi
    else
        log_warning "Cannot run tests without uv"
    fi
else
    log_info "No tests found"
fi

echo ""

# Step 10: Summary
echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${PURPLE}                                Setup Complete!                                   ${NC}"
echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

log_info "Next steps:"
echo "  1. Review PROJECT-PLAN.org for development roadmap"
echo "  2. Check METHODOLOGY.org for development process"
echo "  3. Run 'make help' to see available tasks"
echo "  4. Start first experiment: make experiment-run NAME=001-dice-mechanics"
echo ""

if command -v tmux &> /dev/null; then
    echo "  TMux sessions available:"
    echo "    - tmux attach -t worker1       (mechanics development)"
    echo "    - tmux attach -t worker2       (content & design)"
    echo "    - tmux attach -t coordinator   (integration & testing)"
    echo "    - tmux attach -t meta-coordinator (planning & strategy)"
    echo ""
fi

log_success "Pipeline & Peril development environment is ready!"
echo ""

# Optional: Show project statistics
log_info "Project statistics:"
echo "  Documentation files: $(find . -name "*.org" -type f | wc -l)"
echo "  Python files: $(find . -name "*.py" -type f | wc -l)"
echo "  Experiments: $(ls -d experiments/[0-9]* 2>/dev/null | wc -l)"
echo "  Git commits: $(git rev-list --count HEAD 2>/dev/null || echo "0")"
echo ""

# Set execution flag for convenience
chmod +x "$0"

exit 0