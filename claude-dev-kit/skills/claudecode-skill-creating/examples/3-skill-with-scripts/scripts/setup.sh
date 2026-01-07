#!/usr/bin/env bash

# Project Setup Script
# Initializes a project with essential files and configuration

set -e  # Exit on any error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "\n${BLUE}=== Project Setup ===${NC}\n"

# 1. Initialize git if not already done
if [ ! -d ".git" ]; then
    echo -e "${BLUE}Initializing git repository...${NC}"
    git init
    echo -e "${GREEN}✓ Git initialized${NC}"
else
    echo -e "${GREEN}✓ Git already initialized${NC}"
fi

# 2. Create .gitignore if missing
if [ ! -f ".gitignore" ]; then
    echo -e "${BLUE}Creating .gitignore...${NC}"
    cat > .gitignore << 'EOF'
# Dependencies
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Environment variables
.env
.env.local
.env.*.local

# Build output
dist/
build/
*.log

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Testing
coverage/
.nyc_output/
EOF
    echo -e "${GREEN}✓ Created .gitignore with Node.js defaults${NC}"
else
    echo -e "${GREEN}✓ .gitignore already exists${NC}"
fi

# 3. Create README.md if missing
if [ ! -f "README.md" ]; then
    echo -e "${BLUE}Creating README.md template...${NC}"
    PROJECT_NAME=$(basename "$PWD")
    cat > README.md << EOF
# ${PROJECT_NAME}

## Description

[Add your project description here]

## Installation

\`\`\`bash
npm install
\`\`\`

## Usage

\`\`\`bash
npm start
\`\`\`

## Development

\`\`\`bash
npm run dev
\`\`\`

## Testing

\`\`\`bash
npm test
\`\`\`

## License

[Add license information]
EOF
    echo -e "${GREEN}✓ Created README.md template${NC}"
else
    echo -e "${GREEN}✓ README.md already exists${NC}"
fi

# 4. Create .env.example if .env exists but .env.example doesn't
if [ -f ".env" ] && [ ! -f ".env.example" ]; then
    echo -e "${BLUE}Creating .env.example from .env...${NC}"
    # Create example with keys but empty values
    sed 's/=.*/=/' .env > .env.example
    echo -e "${GREEN}✓ Created .env.example${NC}"
fi

# 5. Install dependencies if package.json exists
if [ -f "package.json" ] && [ ! -d "node_modules" ]; then
    echo -e "${BLUE}Installing dependencies...${NC}"
    npm install
    echo -e "${GREEN}✓ Dependencies installed${NC}"
else
    if [ -d "node_modules" ]; then
        echo -e "${GREEN}✓ Dependencies already installed${NC}"
    fi
fi

# 6. Setup complete
echo -e "\n${GREEN}✓ Setup complete!${NC}\n"

# Display next steps
echo -e "${BLUE}Next steps:${NC}"
echo "1. Review and customize README.md"

if [ -f "package.json" ]; then
    echo "2. Add your project description to package.json"
fi

if [ -f ".env.example" ] || [ -f ".env" ]; then
    echo "3. Configure environment variables in .env"
fi

echo "4. Start coding!"

echo -e "\n${YELLOW}Run 'python scripts/validate.py' to validate your setup${NC}\n"
