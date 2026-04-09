# Ampullary Tool (test version)

This is a first version of my ampullary model tool for internal testing and discussion.  
It is **not packaged**, but can be run locally using a Python virtual environment.

---

## Requirements

- Python **3.10** (tested with 3.10.12)
- Git
- Terminal access

---

## Getting the code

Clone or download the entire project folder from the internal GitHub repository.

The folder structure should look like this:

```
ampullary_ui/
├─ code/
├─ examples/
├─ source/
├─ stimuli/
├─ requirements.txt
└─ README.md


```

## Setup instructions

### 1. Open a terminal and go to the project folder

```bash
cd ampullary_tool
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
```


### 3. Activate the virtual environment

Linux / macOS:

```bash
source venv/bin/activate
```

Windows (PowerShell):

```bash
venv\Scripts\Activate.ps1
```

### 4. Install dependencies

```bash
python -m pip install -r requirements.txt
```

This installs all required packages inside the virtual environment.

#### Installation for usage

```bash
pip install .
# or
make install
```

#### Installation for development

```bash
pip install -e .
# or  
make install-dev
```

This should also build the ``qt`` resources file. If this needs to be done manually,

```bash
python build_resources.py --rcc
# or
make build-resources
```

We further need to compile the qt ``ui`` files that describe the user interface to respective UI classes.

```bash
python build_resources.py --ui
# or
make build-ui
```

## Running the application

When installed, run the UI by calling from the command line

```bash
ampullary-gui
```

If everything works correctly, the application should open.

### Notes

- Do not move files or folders; relative paths inside the app assume the current structure.
- Please give me feedback on functionality, usability, optics and anything that does not work as expected.
- Bounty for all typos: cookies, maybe.


### Notes2
- reset also for cataloge thingy?
- in toolB reset not only after simulation but before as well possible?
- cancel also for simulation? 
- open simuli folder enough, or need some kind of figure there?
- processing fish left or right
- how to use instructions sufficient, or do I need packaging this?

### @Jan
- should i reload posterior inside the subprocess? Because like this i need to pickle and unpickle it a few times? Or no matter since i need to unpickle it to load anyway..
- if simulation is done for 1 cell, i currently save the voltage for baseline. I don't do that for the table version to not create as much data, is that okay or should be changed?
