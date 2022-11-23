import numpy as np
import matplotlib.pyplot as plt
from astropy.cosmology import FlatLambdaCDM, z_at_value
from scipy.special import erf
from scipy.interpolate import interp1d
from tqdm import tqdm

import seaborn as sns
pal=sns.color_palette('colorblind')

import matplotlib as _mpl

_mpl.rcParams['figure.figsize']= (3.3, 2.5)
_mpl.rcParams['figure.dpi']= 300
_mpl.rcParams['axes.labelsize']= 7
_mpl.rcParams['xtick.labelsize']= 7
_mpl.rcParams['ytick.labelsize']= 7
_mpl.rcParams['legend.fontsize']= 7
_mpl.rcParams['font.size']= 7
_mpl.rcParams['font.family']= 'sans-serif'
_mpl.rcParams['font.sans-serif']= ['DejaVu Sans', 'Arial', 'Helvetica', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Avant Garde', 'sans-serif']
_mpl.rcParams['mathtext.fontset']='dejavusans'
_mpl.rcParams['axes.linewidth']= 0.5
_mpl.rcParams['grid.linewidth']= 0.5
_mpl.rcParams['lines.linewidth']= 1.
_mpl.rcParams['lines.markersize']= 3.
_mpl.rcParams['savefig.bbox']= 'tight'
_mpl.rcParams['savefig.pad_inches']= 0.01
#mpl.rcParams['text.latex.preamble']= '\usepackage{amsmath, amssymb, sfmath}'

def normal_distribution(x,mu,sigma):
    '''
    Reuturns a simple gaussian likelihood:
    
    Parameters
    ----------
    x: np.array
        Where to evaluate likelihood
    mu,sigma: np.array
        Mean and standard deviation of gaussian
    '''
    var=sigma**2
    return np.power(2*np.pi*var,-0.5)*np.exp(-0.5*np.power((x-mu)/sigma,2.))

def GW_detection_probability(dltrue,sigmadl,dlthr):
    '''
    Return a detection probability given a gaussian likelihood. The detection probability is defined as 
    the integral from -inf to x_thr of a given normal distribution with mean mu and std.
    
    Parameters
    ----------
    dltrue: np.array
        Where to evaluate the det prob
    sigmadl: np.array
        std of the likelihood model
    dlthr: np.array
        Cut for the selection
    '''
    t_thr= (dlthr-dltrue)/sigmadl # Normalized random variable
    return 0.5*(1+erf(t_thr/np.sqrt(2)))

def GW_detection_probability_Heaviside(dltrue,dlthr):
    '''
    A GW detection probability that is a Heaviside step function 
    
    Parameters
    ----------
    dltrue: np.array
        Where to evaluate the det prob
    dlthr: np.array
        Cut for the selection
    '''
    
    out=np.ones_like(dltrue)
    out[dltrue>dlthr]=0.
    return out

def build_interpolant_TH21(z_true):
    '''
    This function returns the p(z|c) interpolator assuming constant rate. The construction is done as in TH21      arXiv:2112.00241
    
    Parameters
    ----------
    z_true: array
        List of true redshift values for galaxies
    '''
    
    zinterpolant=np.exp(np.linspace(np.log(1e-4),np.log(z_true.max()),50000))
    interpolant=np.zeros_like(zinterpolant)
    
    for i in tqdm(range(len(z_true))):
        sigmaz=0.013*np.power(1+z_true[i],3.)
        if sigmaz>0.015:
            sigmaz=0.015
        interpolant+=normal_distribution(zinterpolant,z_true[i],sigmaz)
    return interp1d(zinterpolant,interpolant,bounds_error=False,fill_value=0.),zinterpolant

def build_interpolant(z_obs,sigmazevalobs,zrate,nocom=False):
    '''
    This function returns the p(z|c) interpolator assuming constant rate
    
    Parameters
    ----------
    z_obs: array
        List of observed values for galaxies
    z_rate: float
        Maximum redshift for the rate
    '''
    
    zinterpolant=np.exp(np.linspace(np.log(1e-3),np.log(zrate),100000))
    
    interpolant=np.zeros_like(zinterpolant)
    cosmo=FlatLambdaCDM(H0=70.,Om0=0.25)
    sigmaz=0.013*np.power(1+zinterpolant,3.)
    sigmaz[sigmaz>0.015]=0.015
       
    # This is the prior to applied to the interpolant 
    if nocom:
        dvcdz_ff=1.
    else:
        dvcdz_ff=cosmo.differential_comoving_volume(zinterpolant).value
 
    for i in tqdm(range(len(z_obs))):
        # Initializes array for the calculation of the interpolant
        zmin=np.max([0.,z_obs[i]-3*sigmazevalobs[i]])
        zeval=np.linspace(zmin,z_obs[i]+5*sigmazevalobs[i],50000)
        sigmazeval=0.013*np.power(1+zeval,3.)
        sigmazeval[sigmazeval>0.015]=0.015
        
        if nocom:
            dvcdz=1.
        else:
            dvcdz=cosmo.differential_comoving_volume(zeval).value
        
        # The line below is the redshift likelihood times the prior.
        pval=normal_distribution(zeval,mu=z_obs[i],sigma=sigmazeval)*dvcdz
        normfact=np.trapz(pval,zeval) # Renormalize
        evals=normal_distribution(zinterpolant,mu=z_obs[i],sigma=sigmaz)*dvcdz_ff/normfact
        if np.all(np.isnan(evals)):
            continue
        interpolant+=evals # Sum to create the interpolant
    interpolant/=np.trapz(interpolant,zinterpolant)
    return interp1d(zinterpolant,interpolant,bounds_error=False,fill_value=0.),zinterpolant

def draw_gw_events(Ndet,sigma_dl,dl_thr,galaxies_list,true_cosmology,zcut_rate):
    '''
    This function draws the GW events and applies a selection based on the observed luminosity distance
    
    Parameters
    ----------
    Ndet: Number of GW detections you want
    sigma_dl: Fractional value of the std for the GW likelihood
    dl_thr: Threshold for detection in Mpc
    galaxies_list: array with the redshift of the galaxies
    true_cosmology: Astropy FlatLambdaCDM class for the true cosmology
    zcut_rate: until what redshift GW events to happen
    
    Returns
    -------
    Observed luminosity distance in Mpc, True luminosity distance in Mpc, True GW redshift, Standard deviation used to draw sample
    '''
    
    Ngw=100000 # Just a random number high enough to have detections
    rate_term = np.zeros_like(galaxies_list) # Initialize the rate term
    rate_term[galaxies_list<=zcut_rate]=1.
     # Draw randomly from the galaxy list, takes into account also a rate cut
    gw_redshift=np.random.choice(galaxies_list,size=Ngw,p=rate_term/rate_term.sum()) 
    gw_true_dl=true_cosmology.luminosity_distance(gw_redshift).to('Mpc').value
    std_dl=gw_true_dl*sigma_dl # Defines the sigma for the gaussian
    gw_obs_dl=np.random.randn(len(gw_true_dl))*std_dl+gw_true_dl # Generate an observed value, a.k.a. data
    gw_detected =  np.where(gw_obs_dl<dl_thr)[0] # Finds the detected GW events
    gw_detected = gw_detected[:Ndet:] # Takes the first Ndet GW events detected
    print('You detected {:d} binaries out of {:d} simulated'.format(len(gw_detected),Ngw))
    
    return gw_obs_dl[gw_detected], gw_true_dl[gw_detected], gw_redshift[gw_detected],std_dl[gw_detected]


def draw_gw_events_TH21(Ndet,sigma_dl,dl_thr,galaxies_list,true_cosmology,zcut_rate):
    '''
    This function draws the GW events and applies a double counting on p(z) as it is done in arXiv:2112.00241
    
    Parameters
    ----------
    Ndet: Number of GW detections you want
    sigma_dl: Fractional value of the std for the GW likelihood
    dl_thr: Threshold for detection in Mpc
    galaxies_list: array with the redshift of the galaxies
    true_cosmology: Astropy FlatLambdaCDM class for the true cosmology
    zcut_rate: until what redshift GW events to happen
    
    Returns
    -------
    Observed luminosity distance in Mpc, True luminosity distance in Mpc, True GW redshift, Standard deviation used to draw sample
    '''
    
    Ngw=100000 # Just a random number high enough to have detections
    rate_term = np.zeros_like(galaxies_list) # Initialize the rate term
    rate_term[galaxies_list<=zcut_rate]=1.
    gw_redshift=np.random.choice(galaxies_list,size=Ngw,p=rate_term/rate_term.sum()) # Draw from galaxies according to rate
    gw_true_dl=true_cosmology.luminosity_distance(gw_redshift).to('Mpc').value
    std_dl=gw_true_dl*sigma_dl
    gw_obs_dl=gw_true_dl
    gw_detected =  np.where(gw_obs_dl<dl_thr)[0]
    gw_detected = gw_detected[:Ndet:]
    print('You detected {:d} binaries out of {:d} simulated'.format(len(gw_detected),Ngw))
    
    return gw_obs_dl[gw_detected], gw_true_dl[gw_detected], gw_redshift[gw_detected],std_dl[gw_detected]


def galaxy_catalog_analysis_accurate_redshift(H0_array,galaxies_list,zcut_rate,gw_obs_dl,sigma_dl,dl_thr):
    '''
    This function will perform the H0 analysis in the limit that the redshift estimate from the catalog
    is without uncertainties
    
    Parameters
    ---------
    H0_array: grid of H0 for the analysis
    galaxies_list: array with the redshift of the galaxies
    zcut_rate: until what redshift GW events to happen
    gw_obs_dl: Array containing observed values for the GW luminosity distance in Mpc
    sigma_dl: Fractional value of the std for the GW likelihood
    dl_thr: Threshold for detection in Mpc
    
    Returns
    -------
    Posterior matrix (raws events, columns H0) and combined posterior
    '''
    
    
    posterior_matrix = np.ones([len(gw_obs_dl),len(H0_array)])
    rate_term = np.zeros_like(galaxies_list)
    rate_term[galaxies_list<=zcut_rate]=1.
    p_z_given_C=rate_term/rate_term.sum() # Calculates what galaxies have a non-zero rate
    cosmotrial=FlatLambdaCDM(H0=70.,Om0=0.25)
    dltimesH0=cosmotrial.luminosity_distance(galaxies_list).to('Mpc').value*cosmotrial.H0.value # Initialize dltimes H0

    for j,H0 in enumerate(H0_array):
        dltrial=dltimesH0/H0 # Calculations of dl
        
        # Selection bias
        selection_bias=np.sum(GW_detection_probability(dltrial,sigmadl=sigma_dl*dltrial,dlthr=dl_thr)*p_z_given_C)
        for i,idx in enumerate(gw_obs_dl):
            # Integral at the numerator (it is a sum since we measure perfectly redshift)
            numerator = np.sum(normal_distribution(gw_obs_dl[i],mu=dltrial,sigma=sigma_dl*dltrial)*p_z_given_C)
            posterior_matrix[i,j]=numerator/selection_bias

    # Normalize and combine posteriors
    combined=np.ones_like(H0_array)
    for i,idx in enumerate(gw_obs_dl):
        posterior_matrix[i,:]/=np.trapz(posterior_matrix[i,:],H0_array)
        combined*=posterior_matrix[i,:]
        combined/=np.trapz(combined,H0_array)
        
    return posterior_matrix,combined

def galaxy_catalog_analysis_photo_redshift_TH21(H0_array,zinterpo,gw_obs_dl,sigma_dl,dl_thr):
    '''
    This function will perform the H0 analysis assuming errors on galaxy redshift but INCORRETLY using and Heaviside step function as GW detection probability.
    
    Parameters
    ---------
    H0_array: grid of H0 for the analysis
    zinterpo: Interpolant for p(z|C)
    gw_obs_dl: Array containing observed values for the GW luminosity distance in Mpc
    sigma_dl: Array of sigma for dl (in Mpc) used to draw gw_obs_dl
    dl_thr: Threshold for detection in Mpc
    
    Returns
    -------
    Posterior matrix (raws events, columns H0) and combined posterior
    '''

    cosmotrial=FlatLambdaCDM(H0=70.,Om0=0.25)
    posterior_matrix = np.ones([len(gw_obs_dl),len(H0_array)])
    # Evaluated d_L times H0
    dltimesH0=cosmotrial.luminosity_distance(zinterpo.x).to('Mpc').value*cosmotrial.H0.value
    selection_bias=np.zeros_like(H0_array)
    pzeval=zinterpo(zinterpo.x)
    
    
    # Calculate the selection effect on the grid just once
    for j,H0 in tqdm(enumerate(H0_array)):
        dltrial=dltimesH0/H0
        integrand=GW_detection_probability_Heaviside(dltrial,sigmadl=sigma_dl*dltrial,dlthr=dl_thr)*pzeval
        selection_bias[j]=np.trapz(integrand,zinterpo.x)
    
    # Loop on the GW events and H0 to compute posteriors
    for i,idx in tqdm(enumerate(gw_obs_dl),desc='Running on GW events'):
        for j,H0 in enumerate(H0_array):
            dltrial=dltimesH0/H0
            integrand=normal_distribution(gw_obs_dl[i],mu=dltrial,sigma=sigma_dl*dltrial)*pzeval
            # Do the integral of the numerator in redshift
            numerator = np.trapz(integrand,zinterpo.x)
            posterior_matrix[i,j]=numerator/selection_bias[j]
            
    # Combine the result
    combined=np.ones_like(H0_array)
    for i,idx in enumerate(gw_obs_dl):
        posterior_matrix[i,:]/=np.trapz(posterior_matrix[i,:],H0_array)
        combined*=posterior_matrix[i,:]
        combined/=np.trapz(combined,H0_array)

    return posterior_matrix,combined



def galaxy_catalog_analysis_photo_redshift(H0_array,zinterpo,gw_obs_dl,sigma_dl,dl_thr):
    '''
    This function will perform the H0 analysis assuming errors on the redshift determination.
    
    Parameters
    ---------
    H0_array: grid of H0 for the analysis
    zinterpo: Interpolant for p(z|C)
    gw_obs_dl: Array containing observed values for the GW luminosity distance in Mpc
    sigma_dl: Array of sigma for dl (in Mpc) used to draw gw_obs_dl
    dl_thr: Threshold for detection in Mpc
    
    Returns
    -------
    Posterior matrix (raws events, columns H0) and combined posterior
    '''

    cosmotrial=FlatLambdaCDM(H0=70.,Om0=0.25)
    posterior_matrix = np.ones([len(gw_obs_dl),len(H0_array)])
    # Evaluated d_L times H0
    dltimesH0=cosmotrial.luminosity_distance(zinterpo.x).to('Mpc').value*cosmotrial.H0.value
    selection_bias=np.zeros_like(H0_array)
    pzeval=zinterpo(zinterpo.x)
    
    
    # Calculate the selection effect on the grid just once
    for j,H0 in tqdm(enumerate(H0_array)):
        dltrial=dltimesH0/H0
        integrand=GW_detection_probability(dltrial,sigmadl=sigma_dl*dltrial,dlthr=dl_thr)*pzeval
        selection_bias[j]=np.trapz(integrand,zinterpo.x)
    
    # Loop on the GW events and H0 to compute posteriors
    for i,idx in tqdm(enumerate(gw_obs_dl),desc='Running on GW events'):
        for j,H0 in enumerate(H0_array):
            dltrial=dltimesH0/H0
            integrand=normal_distribution(gw_obs_dl[i],mu=dltrial,sigma=sigma_dl*dltrial)*pzeval
            # Do the integral of the numerator in redshift
            numerator = np.trapz(integrand,zinterpo.x)
            posterior_matrix[i,j]=numerator/selection_bias[j]
            
    # Combine the result
    combined=np.ones_like(H0_array)
    for i,idx in enumerate(gw_obs_dl):
        posterior_matrix[i,:]/=np.trapz(posterior_matrix[i,:],H0_array)
        combined*=posterior_matrix[i,:]
        combined/=np.trapz(combined,H0_array)

    return posterior_matrix,combined
                
                

    