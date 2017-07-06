# FAICE

FAICE (Fair Collaboration and Experiments) is a tool suite, helping researchers to work with experiments published in
the FAICE description format. The FAICE software is developed at [CBMI](https://cbmi.htw-berlin.de/)
([HTW Berlin](https://www.htw-berlin.de/) - University of Applied Sciences)

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
# validate an experiment description with json schemas built into faice
faice validate -h
```

```bash
# run the specified experiment in an execution engine
faice run -h
```

```bash
# generate a Vagrantfile to launch the specified execution engine in a virtual machine
faice vagrant -h
```

### Parse

FAICE experiments are JSON files, which may contain sensitive information like credentials for data storage or an
execution engine. Instead of publishing an experiment containing these secrets, they should be replaced by variables.
For example `password: "SECRET"` can be replaced with a variable `password: "{{data_password}}"` in double curly braces.
An experiment file containing variables is called **template**. The syntax for variables is borrowed from the Python
templating engine Jinja2 and other similar templating engines used in various programming languages.

The `faice parse` tool takes an experiment template as input and helps with filling out any undeclared variables.
The resulting experiment file will be written to the file system and can be used with other FAICE tools. If the
appropriate value for a certain variable is unknown it can be left blank, as long as the resuling JSON file is valid.
Take a look at the remaining FAICE tools to use an experiment file generated with `faice parse`.

### Validate

The `faice validate` tool can be used to validate the format of an **experiment** JSON file.

### Run

The `faice run` tool runs the given **experiment** by sending the instructions contained in the experiment JSON file to
the specified execution engine. If the experiment JSON file was generated from an experiment template and not all
variables have been filled with correct values, it is advised to check the `faice vagrant` tool, before trying to run
an experiment.

### Vagrant

If the **experiment** JSON file was generated from an experiment template and not all variables have been filled with
correct values, the `faice vagrant` tool can be used to set up a local execution engine. When using a local execution
engine, it is not necessary to know any secret credentials for online resources.

This local execution engine runs in a Vagrant virtual machine (VM), where all necessery configuration files
are generated by `faice vagrant`. It can be used in two different ways: either to run an experiment in the VM and
still use remote data repositories for input and result files, or to run an experiment in the VM and read input files
from a local file system directory, as well as saving result files locally.
