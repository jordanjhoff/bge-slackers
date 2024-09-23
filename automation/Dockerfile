# automation/Dockerfile

# parent image
FROM python:3.11-slim

WORKDIR /usr/src/app

# requirements file into the container
COPY requirements.txt ./

# python packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# EXPOSE 3000

CMD ["python", "./automation_script.py"]
