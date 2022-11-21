# Dark Standard Sirens 101: A guide to the galaxy catalog approach for gravitational wave cosmology

This repository hosts the data distribution of Dark Standard Sirens 101: A guide to the galaxy catalog approach for gravitational wave cosmology. To run the code, just clone the repository with 

```
git clone https://github.com/simone-mastrogiovanni/dark_sirens_101
```

and then use the notebooks and scripts in the repository

## Software requirements

You will need a working copy of python v>=3.8 with the packages `astropy, numpy, scipy, matplotlib, tqdm`.

## Content's short description

In the repository you will find several notebooks

* `gal4H0.py`: Is the module containing all the functions for the toy model. It also contains the functions to run the H0 analysis.

* `H0analysis.ipynb`: Is the notebook showing the Galaxy catalog approach with simulated GW events from MICEcat. In this notebook, you can also change several parameters of the 

* `H0analysis_realuniform.ipynb`: Generate Hubble constant posteriors using the Toy model but this time with galaxies distribuited uniform in the comoving volume.

* `H0analysis_TH21.ipynb`: Run the H0 analysis but making some wrong assumptions similar to TH21 (see paper for more description). The two inconsistent analyses make use of a Heaviside GW detection probability and double counting galaxies when drawing GW events.

* `ppplots.ipynb`: Reads files containing H0 posteriors from more than 20000 GW events to generate PP plots and convergence plots for the H0 precision. The data that the notebook reads is generated with the python scripts in `high_Ndet_data` and `ppplots_data`.

* `plotting_101.ipynb`: Contains some plotting such as the GW detection probability. 

* `MICECAT_LOS:` Contains the MICECAT line-of-sights used