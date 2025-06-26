#!/bin/bash

echo "Setting up Streaming Chatbot Backend..."

# Create virtual environment
echo "Creating virtual environment..."
python -m venv chatbot_env

# Activate virtual environment
echo "Activating virtual environment..."
source chatbot_env/bin/activate  # For Linux/Mac
# chatbot_env\Scripts\activate  # For Windows

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create PostgreSQL database (assuming PostgreSQL is installed)
echo "Setting up PostgreSQL database..."
echo "Please make sure PostgreSQL is running and create a database named 'chatbot_db'"
echo "You can do this by running:"
echo "  createdb chatbot_db"
echo "Or using psql:"
echo "  psql -c 'CREATE DATABASE chatbot_db;'"

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Update the .env file with your database credentials and OpenAI API key"
echo "2. Make sure PostgreSQL is running"
echo "3. Run the application with: python main.py"
echo "4. Test the API with: python test_streaming.py"