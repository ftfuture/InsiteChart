#!/bin/bash

# InsiteChart Docker Compose Startup Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENV_FILE="${1:-.env.docker}"
COMPOSE_FILE="docker-compose.yml"
PROD_MODE="${2:-dev}"

# Functions
print_header() {
    echo -e "${BLUE}============================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Check requirements
check_requirements() {
    print_header "Checking Requirements"

    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        exit 1
    fi
    print_success "Docker is installed"

    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed"
        exit 1
    fi
    print_success "Docker Compose is installed"

    if [ ! -f "$ENV_FILE" ]; then
        print_warning "Environment file '$ENV_FILE' not found"
        print_warning "Creating from defaults..."
        cp .env.example "$ENV_FILE" 2>/dev/null || {
            print_warning "Using default environment variables"
        }
    fi
    print_success "Environment configured"
}

# Setup environment
setup_environment() {
    print_header "Setting Up Environment"

    # Create required directories
    mkdir -p logs
    mkdir -p data/postgres
    mkdir -p data/redis

    print_success "Directories created"

    # Load environment
    export $(cat "$ENV_FILE" | grep -v '^#' | xargs)
    print_success "Environment variables loaded"
}

# Build images
build_images() {
    print_header "Building Docker Images"

    if [ "$PROD_MODE" == "prod" ]; then
        docker-compose -f "$COMPOSE_FILE" build --no-cache
    else
        docker-compose -f "$COMPOSE_FILE" build
    fi

    print_success "Images built successfully"
}

# Start services
start_services() {
    print_header "Starting Services"

    if [ "$PROD_MODE" == "prod" ]; then
        docker-compose -f "$COMPOSE_FILE" -f docker-compose.prod.yml up -d
    else
        docker-compose -f "$COMPOSE_FILE" -f docker-compose.override.yml up -d
    fi

    print_success "Services started"
}

# Wait for services
wait_for_services() {
    print_header "Waiting for Services to Be Ready"

    local max_attempts=30
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if curl -sf http://localhost:8080/health > /dev/null 2>&1; then
            print_success "API Gateway is ready"
            break
        fi

        attempt=$((attempt + 1))
        echo -ne "${YELLOW}Waiting for services... ($attempt/$max_attempts)${NC}\r"
        sleep 2
    done

    if [ $attempt -eq $max_attempts ]; then
        print_error "Services failed to start within timeout"
        return 1
    fi

    # Wait a bit more for other services
    sleep 5
}

# Display service information
show_service_info() {
    print_header "InsiteChart Services"

    echo -e "${GREEN}Services available at:${NC}"
    echo -e "  API Gateway:       ${BLUE}http://localhost:8080${NC}"
    echo -e "  Backend:           ${BLUE}http://localhost:8000${NC}"
    echo -e "  Data Collector:    ${BLUE}http://localhost:8001${NC}"
    echo -e "  Analytics:         ${BLUE}http://localhost:8002${NC}"
    echo -e "  Frontend:          ${BLUE}http://localhost:8501${NC}"
    echo ""
    echo -e "${GREEN}Useful commands:${NC}"
    echo -e "  View logs:         ${YELLOW}docker-compose logs -f${NC}"
    echo -e "  Stop services:     ${YELLOW}docker-compose down${NC}"
    echo -e "  Shell access:      ${YELLOW}docker-compose exec <service> bash${NC}"
    echo ""
    echo -e "${GREEN}Demo credentials:${NC}"
    echo -e "  Username: demo_user"
    echo -e "  Password: demo_password"
}

# Main execution
main() {
    print_header "InsiteChart Docker Compose Setup"

    echo -e "${BLUE}Mode: $PROD_MODE${NC}"
    echo -e "${BLUE}Environment file: $ENV_FILE${NC}"

    check_requirements
    setup_environment
    build_images
    start_services

    if wait_for_services; then
        show_service_info
        print_success "All services are running!"
        exit 0
    else
        print_error "Failed to start services"
        echo ""
        echo "Checking service logs:"
        docker-compose logs --tail=50
        exit 1
    fi
}

# Run main
main
