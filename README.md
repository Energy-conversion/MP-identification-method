# MP-identification-method
A Method for Identifying Aged Microplastics Using Raman Spectroscopy  
  
Input your spectrum (in .txt format) and obtain a microplastic identification result for reference.  
An example text file has been provided.  
  
Important Notes:  
1.	Before using this method, please ensure that your spectra have been baseline-corrected and that peak positions are accurately calibrated.  
2.	The degree of baseline correction can be adjusted with reference to the standard spectra provided in the Excel files.  
3.	This program uses linear interpolation to upsample the data points of your spectral curve.  
4.	The matching degree is evaluated based on the Pearson correlation coefficient.  
5.	Depending on the delimiter used in your file, you may need to modify the separation condition in line 55 of the code to ensure proper execution.  
6.	You are welcome to use or modify the standard spectral library provided in the Excel files for non-commercial purposes, without prejudice to our rights.
    
The current version of the library is not yet available for public access. Please feel free to contact us if you require further information or wish to be notified upon its release.  
We welcome your feedback on this detection method—including its application scenarios and effectiveness.  
As the detection schemes for microplastics are not yet standardized, there remains significant room for optimization. If you have any suggestions or would like to collaborate, please feel free to reach out to us.  
Contact e-mail: suting231@mails.ucas.ac.cn  
Instrumentation Used:  
•	Instrument: LabRAM HP Evolution, Horiba Scientific, France  
•	Laser Wavelength: 532 nm  
