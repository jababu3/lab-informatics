#!/bin/bash
echo "🧪 Lab Informatics Setup"
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ Created .env - edit with your passwords"
else
    echo "✅ .env exists"
fi
chmod +x scripts/*
echo "Next: make start"
