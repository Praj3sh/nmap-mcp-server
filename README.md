# nmap-mcp-server
An easy Model Context Protocol (MCP) server for Nmap with controlled scan profiles and safety rails. Integrates with Claude Desktop as shown in the demo below


## Prerequisites

- **Linux system** (tested on Kali Linux)
- **Python 3.10+**
  - Python includes the built-in `venv` module
  - On some distributions you may need to install `python3-venv`
- **Nmap**
- **libcap / setcap**
  - Required to grant Nmap network capabilities
- **An MCP-compatible AI client**
  - Example: Claude Desktop (follow instructions here: https://github.com/aaddrick/claude-desktop-debian (I installed package as `.deb` so that google login works))

 ## Configuration

Edit nmap_config.json

      "command": "/path/to/project_directory/venv/bin/python",
      "args": ["/path/to/project_directory/nmap_server.py"]
Replace `/path/to/project_directory` to the path to the actual file path.

Make the `run.sh` file executable

      chmod +x run.sh                     

If using Claude Desktop,

 add or rename `nmap_config.json` to `claude_desktop_config.config` and move to `~/.config/Claude/`
 
 If you cannot find the folder
   - open Claude Desktop app
   - go to Settings
   - go to Developer under Desktop app
   - click on "Edit Config"
   - either move `claude_desktop_configuration.config` to folder or if there is already one present, edit as such:

   <img width="553" height="423" alt="image" src="https://github.com/user-attachments/assets/c8d5a9f8-819d-4118-92a3-24ce1bf5ad27" />


## Starting and using with Claude Desktop

      sudo ./run.sh            

<img width="870" height="567" alt="image" src="https://github.com/user-attachments/assets/b93e8104-f8d3-491d-ba4f-e1997a702dd0" />

Press Control + C to stop server when needed.
After starting server, open Claude and check if nmap server is running in Developer settings or asking for the list of available tools in the prompt input.


## Using Claude Desktop in Kali Linux

Permission requests are set up so that it does not do something unintended and the user can stop it at any point.

<img width="740" height="371" alt="image" src="https://github.com/user-attachments/assets/49c14431-098b-4c41-a877-b65f5a912b14" />

<img width="731" height="391" alt="image" src="https://github.com/user-attachments/assets/96678048-609b-4c48-8f53-aab4d392da64" />

<img width="744" height="318" alt="image" src="https://github.com/user-attachments/assets/3b179bfe-a090-4f81-b98d-195e5b2257d7" />

<img width="520" height="636" alt="image" src="https://github.com/user-attachments/assets/7a05258c-a9dd-4e3d-9c0a-6e9ce34a218d" />

