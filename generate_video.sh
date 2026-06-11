#!/bin/bash
# Install the python virtualenv and DevPilot
python3 -m venv ~/devpilot_venv
source ~/devpilot_venv/bin/activate
pip install -e .

# Run VHS to generate the video
vhs tutorial_wsl.tape

echo "Video generation complete! Check devpilot_demo.gif and devpilot_demo.mp4"
