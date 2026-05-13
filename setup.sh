#!/bin/bash
echo "Setting up Topology Tormentor Lite..."

if ! command -v python3 &> /dev/null
then
    echo "Error: Python 3 is not installed. Please install it to continue."
    exit 1
fi

echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Creating launch script..."
cat <<EOF > ttl-launch.sh
#!/bin/bash
source venv/bin/activate
python3 main.py
EOF
chmod +x ttl-launch.sh

echo "------------------------------------------------"
echo "Setup Complete!"
echo "To start the simulator, run: ./ttl-launch.sh"
echo "------------------------------------------------"
