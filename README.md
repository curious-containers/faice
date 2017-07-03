# FAICE

FAICE (Fair Collaboration and Experiments) is a tool suite, helping researchers to work with experiments published in
the FAICE description format. The FAICE software is developed at [CBMI](https://cbmi.htw-berlin.de/) ([HTW Berlin](https://www.htw-berlin.de/) - University of Applied Sciences)

## Install

FAICE is a cross-platform software implemented in Python 3 and can be installed via Python's package manager pip.
Make sure to use the Python 3 version of pip, usually referred to as pip3.

```bash
pip3 install --user faice
```

## Usage

FAICE provides various tools via a common command line interface. The help commands `faice ${tool} -h`
provide additional information about each tool.

```bash
# list available tools
faice
```

```bash
# parse experiment template to fill in undeclared variables
faice parse -h
```

```bash
# adapt an experiment to your own needs
faice adapt -h
```

```bash
# validate an experiment description with json schemas built into faice
faice validate -h
```

```bash
# generate a Vagrantfile to launch the specified execution engine in a virtual machine
faice vagrant -h
```

```bash
# run the specified experiment in an execution engine
faice run -h
```
