/******************************************************************************
 * COMMON SAS SIMULATION SETUP
 *
 * Purpose: Define common macro variables for all simulation scenarios:
 *          - CASL simulation
 *          - Base SAS Viya simulation
 *          - Base SAS Local simulation
 *
 * Usage: %include "setup.sas";
 *
 * Author: Vikas Gaddu
 * Date: 2025-09-22
 * Version: 1.0 - Common setup for all simulation types
 ******************************************************************************/

%put NOTE: Loading common simulation setup...;

/*=============================================================================
 * SECTION 1: SIMULATION PARAMETERS
 *============================================================================*/

/* Sample size parameters */
%let nst1 = 50;      /* Stage 1: subjects per treatment arm */
%let nst2 = 50;      /* Stage 2: initial subjects per treatment arm */
%let nmax = 75;      /* Stage 2: maximum subjects per arm (for promising zone) */

/* Simulation parameters */
%let iter = 1;      /* Number of simulation iterations (use 10,000-100,000 for production) */

/* Random seeds for reproducibility */
%let seed11i = 1;    /* Stage 1, treatment 0 */
%let seed21i = 4;    /* Stage 1, treatment 1 */
%let seed12i = 2;    /* Stage 2, treatment 0 */
%let seed22i = 3;    /* Stage 2, treatment 1 */

/* Statistical boundaries and thresholds */
%let cst1 = 3.586925;    /* Stage 1 critical value (Hwang-Shih-DeCani, gamma=-10) */
%let cst2 = 1.960395;    /* Stage 2 critical value (approximately z_0.975) */
%let beta = 0.01;        /* Type II error rate (power = 1 - beta = 0.99) */

/* Conditional power thresholds for decision zones */
%let cp1fut = 0.10;      /* Futility boundary (stop if CP < 0.10) */
%let cp1lowpz = 0.30;    /* Lower promising zone boundary */
%let cp2highpz = 0.90;   /* Upper promising zone boundary */

/* Output file names */
%let outd = modsum_base.xlsx;    /* Summary statistics by region */
%let outd2 = modOC_base.xlsx;     /* Detailed simulation results */

%put NOTE: Common setup loaded successfully.;
%put NOTE: Sample size parameters - Nst1: &nst1, Nst2: &nst2, Nmax: &nmax;
%put NOTE: Simulation iterations: &iter;
%put NOTE: Statistical boundaries - Cst1: &cst1, Cst2: &cst2;
