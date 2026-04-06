# ECNG-3020-IEEE-SESDC-microgrid_design_toolkit-backend-python

Microgrids are an important use of renewable energy resources by providing sustainable energy to underserved communities. However, many microgrids projects fail due lack consideration of environmental and operational factors.
This repository presents the development of a modular optimisation framework for microgrid system design, with a focus on cost-effective component selection under varying environmental and operational conditions.
 See the attached link below to view the wiki detailing the design methods.
 
[Wiki](https://github.com/Vidal-Mastay/ECNG-3020-IEEE-SESDC-microgrid_design_toolkit-backend-python/wiki)


## Objectives

- Support informed decision-making in preliminary microgrid design.
- Provide a framework for optimal (cost-effective) sizing of microgrid components incoperating environmental and operational factors.
- Provide a set of Python methods allowing users to obtain results pertaining to optimal microgrid component selection and cost projections.

---

## Dependencies
The following are a list of the main dependencies required to run the developed methods.(See `requirements.txt` for all dependencies)
1.	Python
2.	Pandas library
3.	Numpy library
4.	CVXPY library
5.	Jupyter notebook
6.	HiGHS
7. matplotlib

Installing the aforementioned dependencies can be done as shown below:
```bash
pip install cvxpy
```
---

## Installation 
1. Clone repository
2. Install aforementioned dependencies
3. Setup repository in preferred environment.

## Running 

1. To utilise the developed methods in another file the user is required to import the file and class they intended to use.
```py
from IEEESESDCbackendmethodspython import Optimisation
```

2. Any method can be accessed by instantiating a variable to either of the respective classes. However it is preferred that a user instantiates to the `Optimisation` class to access all methods since it inherits from the `DataRead` class. For example:

```py
case_study=Optimisation()
```
3. Once the class variable is instantiated the methods can be used to obtain the results given from data, in the form of a CSV (Example `Data_File_4.csv`) and various imputs to the `solution_setup` method. An example of the general expected work flow is shown below:
```py
case_study.read_in_data('Data_File_4.csv')
case_study.solution_setup(20,500,0,100,5000,0.30,9,8)
case_study.Solving()
initial_list, replacement_list=case_study.component_list()
```
`Usecase_notebook` is a Jupyter notebook further detailing uses case of the developed methods.

## Author
Vidal Mastay @Vidal-Mastay
