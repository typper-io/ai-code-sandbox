import docker
import shlex
import uuid
import textwrap
import os
import tarfile
import io
from io import BytesIO
import time

class AICodeSandbox:
    """
    A sandbox environment for executing Python code safely.

    This class creates a Docker container with a Python environment,
    optionally installs additional packages, and provides methods to
    execute code, read and write files within the sandbox.

    Attributes:
        client (docker.DockerClient): Docker client for managing containers and images.
        container (docker.models.containers.Container): The Docker container used as a sandbox.
        temp_image (docker.models.images.Image): Temporary Docker image created for the sandbox.
    """

    def __init__(self, custom_image=None, packages=None, network_mode="none", mem_limit="100m", cpu_period=100000, cpu_quota=50000):
        """
        Initialize the PythonSandbox.

        Args:
            custom_image (str, optional): Name of a custom Docker image to use. Defaults to None.
            packages (list, optional): List of Python packages to install in the sandbox. Defaults to None.
            network_mode (str, optional): Network mode to use for the sandbox. Defaults to "none".
            mem_limit (str, optional): Memory limit for the sandbox. Defaults to "100m".
            cpu_period (int, optional): CPU period for the sandbox. Defaults to 100000.
            cpu_quota (int, optional): CPU quota for the sandbox. Defaults to 50000.
        """
        self.client = docker.from_env()
        self.container = None
        self.temp_image = None
        self._setup_sandbox(custom_image, packages, network_mode, mem_limit, cpu_period, cpu_quota)

    def _setup_sandbox(self, custom_image, packages, network_mode, mem_limit, cpu_period, cpu_quota):
        """Set up the sandbox environment."""
        image_name = custom_image or "python:3.9-slim"
        
        if packages:
            dockerfile = f"FROM {image_name}\nRUN pip install {' '.join(packages)}"
            dockerfile_obj = BytesIO(dockerfile.encode('utf-8'))
            self.temp_image = self.client.images.build(fileobj=dockerfile_obj, rm=True)[0]
            image_name = self.temp_image.id

        self.container = self.client.containers.run(
            image_name,
            name=f"python_sandbox_{uuid.uuid4().hex[:8]}",
            command="tail -f /dev/null",
            detach=True,
            network_mode=network_mode,
            mem_limit=mem_limit,
            cpu_period=cpu_period,
            cpu_quota=cpu_quota
        )

    def write_file(self, filename, content):
        """
        Write content to a file in the sandbox, creating directories if they don't exist.

        Args:
            filename (str): Name of the file to create or overwrite.
            content (str): Content to write to the file.

        Raises:
            Exception: If writing to the file fails.
        """
        directory = os.path.dirname(filename)
        if directory:
            mkdir_command = f'mkdir -p {shlex.quote(directory)}'
            mkdir_result = self.container.exec_run(["sh", "-c", mkdir_command])
            if mkdir_result.exit_code != 0:
                raise Exception(f"Failed to create directory: {mkdir_result.output.decode('utf-8')}")

        tar_stream = io.BytesIO()
        with tarfile.open(fileobj=tar_stream, mode='w') as tar:
            file_data = content.encode('utf-8')
            tarinfo = tarfile.TarInfo(name=filename)
            tarinfo.size = len(file_data)
            tar.addfile(tarinfo, io.BytesIO(file_data))

        tar_stream.seek(0)

        try:
            self.container.put_archive('/', tar_stream)
        except Exception as e:
            raise Exception(f"Failed to write file: {str(e)}")

        check_command = f'test -f {shlex.quote(filename)}'
        check_result = self.container.exec_run(["sh", "-c", check_command])
        if check_result.exit_code != 0:
            raise Exception(f"Failed to write file: {filename}")

    def read_file(self, filename):
        """
        Read content from a file in the sandbox.

        Args:
            filename (str): Name of the file to read.

        Returns:
            str: Content of the file.

        Raises:
            Exception: If reading the file fails.
        """
        result = self.container.exec_run(["cat", filename])
        if result.exit_code != 0:
            raise Exception(f"Failed to read file: {result.output.decode('utf-8')}")
        return result.output.decode('utf-8')

    def run_code(self, code, env_vars=None):
        """
        Execute Python code in the sandbox.

        Args:
            code (str): Python code to execute.
            env_vars (dict, optional): Environment variables to set for the execution. Defaults to None.

        Returns:
            str: Output of the executed code or error message.
        """
        if env_vars is None:
            env_vars = {}
        
        code = textwrap.dedent(code)

        env_str = " ".join(f"{k}={shlex.quote(v)}" for k, v in env_vars.items())
        escaped_code = code.replace("'", "'\"'\"'")
        exec_command = f"env {env_str} python -c '{escaped_code}'"
        
        exec_result = self.container.exec_run(
            ["sh", "-c", exec_command],
            demux=True
        )
        
        if exec_result.exit_code != 0:
            return f"Error (exit code {exec_result.exit_code}): {exec_result.output[1].decode('utf-8')}"
        
        stdout, stderr = exec_result.output
        if stdout is not None:
            return stdout.decode('utf-8')
        elif stderr is not None:
            return f"Error: {stderr.decode('utf-8')}"
        else:
            return "No output"

    def close(self):
        """
        Remove all resources created by this sandbox.

        This method should be called when the sandbox is no longer needed to clean up Docker resources.
        """
        if self.container:
            try:
                self.container.stop(timeout=10)
                self.container.remove(force=True)
            except Exception as e:
                print(f"Error stopping/removing container: {str(e)}")
            finally:
                self.container = None

        time.sleep(2)

        if self.temp_image:
            try:
                for _ in range(3):
                    try:
                        self.client.images.remove(self.temp_image.id, force=True)
                        break
                    except Exception as e:
                        print(f"Attempt to remove image failed: {str(e)}")
                        time.sleep(2)
                else:
                    print("Failed to remove temporary image after multiple attempts")
            except Exception as e:
                print(f"Error removing temporary image: {str(e)}")
            finally:
                self.temp_image = None

    def __del__(self):
        """Ensure resources are cleaned up when the object is garbage collected."""
        self.close()