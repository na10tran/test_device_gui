FROM ubuntu:22.04

RUN apt-get update && apt-get install -y build-essential

# Set working directory to /app/device_sim
WORKDIR /app

# Copy your entire project into the container
COPY . .

# Change into device_sim folder and build
WORKDIR /app/device_sim
RUN make

# Run the built device from device_sim folder
ENTRYPOINT ["./device"]
CMD ["--deterministic", "-v"]
