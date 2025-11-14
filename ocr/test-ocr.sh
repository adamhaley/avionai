#!/bin/bash
# Test the OCR server with a sample image

PORT=${1:-8080}
IMAGE=${2:-test.png}

echo "Testing OCR server on port $PORT..."

# Check if server is running
if ! curl -s http://localhost:$PORT/health > /dev/null; then
    echo "Error: Server is not running on port $PORT"
    echo "Start it with: ./start-server.sh $PORT"
    exit 1
fi

echo "Server is healthy!"

# Check if test image exists
if [ ! -f "$IMAGE" ]; then
    echo "Creating test image..."
    convert -size 400x100 -background white -fill black \
            -font DejaVu-Sans -pointsize 32 \
            label:"Hello World OCR Test" \
            test.png 2>/dev/null || {
        echo "Note: ImageMagick not installed. Please provide your own test image."
        echo "Usage: $0 [port] [image_file]"
        exit 1
    }
fi

echo "Sending image to OCR endpoint..."
curl -X POST "http://localhost:$PORT/ocr" \
     -F "file=@$IMAGE" \
     -H "accept: application/json" | jq .

echo ""
echo "Test complete!"
