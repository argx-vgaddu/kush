/******************************************************************************
 * ADAPTIVE CLINICAL TRIAL SIMULATION WITH CONDITIONAL POWER - BASE SAS VERSION
 *
 * Purpose: This program simulates a two-stage adaptive clinical trial design
 *          with interim analysis based on conditional power calculations.
 *
 * This version includes common setup variables for consistency across environments.
 *
 * Key Features:
 * - Stage 1: Initial trial with fixed sample size
 * - Interim Analysis: Conditional power calculation to determine next steps
 * - Stage 2: Continuation with potentially adapted sample size
 * - Operating Characteristics: Power, sample size, and region probabilities
 *
 * Author: Vikas Gaddu
 * Date: 2025-09-22
 * Version: 2.1 - Base SAS Implementation with common setup include
 ******************************************************************************/

/*=============================================================================
 * SECTION 1: PROGRAM HEADER
 *============================================================================*/

/* Note: Setup parameters are now included programmatically by the Python script */

/*=============================================================================
 * SECTION 2: ENVIRONMENT-SPECIFIC SETTINGS
 * Define paths specific to the Viya environment
 *============================================================================*/

/* File paths for input data and output results */
%let data_path = /xar/general/biostat/jobs/gadam_ongoing_studies/prod/programs/vgaddu/CASL/data;
%let output_path = /xar/general/biostat/jobs/gadam_ongoing_studies/prod/programs/vgaddu/CASL/output/;

/* Input correlation data files */
%let file1 = &data_path./simdata1.csv;  /* Treatment group 0 correlation structure */
%let file2 = &data_path./simdata2.csv;  /* Treatment group 1 correlation structure */

/*=============================================================================
 * SECTION 3: MACRO DEFINITIONS
 *============================================================================*/

/**
 * MACRO: simulate_and_process
 * Purpose: Generate simulated multivariate normal data and transform to long format
 *          for a single treatment group
 * 
 * Parameters:
 *   input_data   - Correlation dataset for simulation
 *   output_prefix - Base name for output datasets
 *   seed         - Random seed for reproducibility
 *   nst          - Number of subjects per iteration
 *   iter         - Number of iterations to simulate
 *   sid_offset   - Offset for subject ID (ensures unique IDs across groups)
 *   trt_value    - Treatment indicator (0 or 1)
 */
%macro simulate_and_process(
    input_data=,
    output_prefix=,
    seed=,
    nst=,
    iter=,
    sid_offset=0,
    trt_value=
);
    /* Step 1: Generate multivariate normal data preserving correlation structure */
    proc simnormal data=&input_data 
                   outsim=&output_prefix
                   numreal=%sysevalf(&nst*&iter) 
                   seed=&seed;         
        var y1-y10;  /* 10 time points */
    run;
    
    /* Step 2: Create iteration and subject identifiers */
    data &output_prefix._sid;
        set &output_prefix;
        iterID = floor((_N_-1) / &nst) + 1;  /* Iteration number */
        
        /* Calculate subject ID with optional offset */
        %if &sid_offset > 0 %then %do;
            SID = mod(rnum, &nst) + &sid_offset + 1;
        %end;
        %else %do;
            SID = mod(rnum, &nst) + 1;
        %end;
        
        drop rnum; 
    run;
    
    /* Step 3: Sort for transpose */
    proc sort data=&output_prefix._sid;
        by iterID SID;
    run;
    
    /* Step 4: Reshape from wide to long format */
    proc transpose data=&output_prefix._sid 
                   out=&output_prefix._long;
        by iterID SID;
        var y1-y10;
    run;
    
    /* Step 5: Add time and treatment variables */
    data &output_prefix._long_t;
        set &output_prefix._long (rename=(col1=y));
        t = input(substr(_name_, 2), 2.);  /* Extract time point (1-10) */
        visit = cat("t", input(substr(_name_, 2), 2.));  /* Visit label */
        trt = &trt_value;  /* Treatment assignment */
        drop _name_;
    run;

%mend simulate_and_process;

/**
 * MACRO: combine_and_calculate_change
 * Purpose: Combine two treatment groups and calculate change from baseline
 * 
 * Parameters:
 *   dbs1_prefix  - Prefix for treatment group 0 datasets
 *   dbs2_prefix  - Prefix for treatment group 1 datasets
 *   output_data  - Name of final output dataset
 */
%macro combine_and_calculate_change(
    dbs1_prefix=,
    dbs2_prefix=,
    output_data=
);
    /* Combine both treatment groups */
    data sim_dbs_long_t_comb;
        set &dbs1_prefix._long_t &dbs2_prefix._long_t;
    run;
    
    /* Extract baseline values (t=1) */
    data sim_dbs_long_t_bsl;
        set sim_dbs_long_t_comb;
        if t = 1;  /* Keep only baseline observations */
        rename y = bsl;
    run;
    
    /* Sort for merge */
    proc sort data=sim_dbs_long_t_comb;
        by SID iterID;
    run;
    
    proc sort data=sim_dbs_long_t_bsl;
        by SID iterID;
    run;
    
    /* Merge baseline with all timepoints */
    data sim_dbs_long_t_comb_bsl;
        merge sim_dbs_long_t_comb sim_dbs_long_t_bsl;
        by SID iterID;
    run;
    
    /* Calculate change from baseline */
    data &output_data;
        set sim_dbs_long_t_comb_bsl;
        chg = y - bsl;  /* Change from baseline */
        if t = 1 then chg = .;  /* No change at baseline */
    run;
    
    /* Final sort */
    proc sort data=&output_data;
        by iterID SID;
    run;
    
    /* Clean up temporary datasets */
    proc delete data=sim_dbs_long_t_comb 
                     sim_dbs_long_t_bsl 
                     sim_dbs_long_t_comb_bsl; 
    run;

%mend combine_and_calculate_change;

/**
 * MACRO: simdatst2
 * Purpose: Simulate Stage 2 data for each iteration based on Stage 1 results
 */
%macro simdatst2;
    %do icnt = 1 %to &iter;
        %let n2st2 = 0;
        
        /* Get Stage 2 sample size from Stage 1 results */
        data _null_;
            set res1a;
            if iterID = &icnt then 
                call symput('n2st2', trim(left(put(N2new, 4.))));
        run;
        
        /* Generate iteration-specific seeds */
        %let sed1 = %sysfunc(ceil(&seed12i + 10*&icnt));
        %let sed2 = %sysfunc(ceil(&seed22i + 3*&icnt));
        
        /* Simulate both treatment groups for this iteration */
        %simulate_and_process(
            input_data=dbsim1c,
            output_prefix=sim_dbs1_iter&icnt,
            seed=&sed1,
            nst=&nst2,
            iter=1,
            sid_offset=0,
            trt_value=0
        );
        
        %simulate_and_process(
            input_data=dbsim2c,
            output_prefix=sim_dbs2_iter&icnt,
            seed=&sed2,
            nst=&nst2,
            iter=1,
            sid_offset=&nst2,
            trt_value=1
        );
        
        /* Combine groups and calculate change from baseline */
        %combine_and_calculate_change(
            dbs1_prefix=sim_dbs1_iter&icnt,
            dbs2_prefix=sim_dbs2_iter&icnt,
            output_data=dat_stg2iter&icnt
        );
        
        /* Add iteration ID */
        data dat_stg2iter&icnt;
            set dat_stg2iter&icnt;
            iterID = &icnt;
        run;
        
        /* Append to main Stage 2 dataset */
        data dat_stg2;
            set dat_stg2 dat_stg2iter&icnt;
        run;
        
        /* Clean up iteration-specific datasets */
        proc delete data=dat_stg2iter&icnt
                        sim_dbs1_iter&icnt
                        sim_dbs2_iter&icnt
                        sim_dbs1_iter&icnt._sid
                        sim_dbs2_iter&icnt._sid
                        sim_dbs1_iter&icnt._long
                        sim_dbs2_iter&icnt._long
                        sim_dbs1_iter&icnt._long_t
                        sim_dbs2_iter&icnt._long_t; 
        run;
    %end;
%mend simdatst2;

/*=============================================================================
 * SECTION 4: MAIN SIMULATION EXECUTION
 *============================================================================*/

/*-----------------------------------------------------------------------------
 * STAGE 1: DATA PREPARATION AND INITIAL SIMULATION
 *----------------------------------------------------------------------------*/

/* Import correlation data from Excel files */
proc import datafile="&file1" 
            DBMS=csv 
            OUT=dbsim1;
run;

proc import datafile="&file2" 
            DBMS=csv 
            OUT=dbsim2;
run;

/* Create correlation datasets for simulation */
data dbsim1c(type=corr);
    set dbsim1;
run;

data dbsim2c(type=corr);
    set dbsim2;
run;

/* Generate Stage 1 simulated data - Call macro twice */
%simulate_and_process(
    input_data=dbsim1c,
    output_prefix=sim_dbs1,
    seed=&seed11i,
    nst=&nst1,
    iter=&iter,
    sid_offset=0,
    trt_value=0
);

%simulate_and_process(
    input_data=dbsim2c,
    output_prefix=sim_dbs2,
    seed=&seed21i,
    nst=&nst1,
    iter=&iter,
    sid_offset=&nst1,
    trt_value=1
);

/* Combine Stage 1 data and calculate change from baseline */
%combine_and_calculate_change(
    dbs1_prefix=sim_dbs1,
    dbs2_prefix=sim_dbs2,
    output_data=dat_stg1
);

/* Clean up intermediate Stage 1 datasets */
proc delete data=sim_dbs1 sim_dbs2
                 sim_dbs1_sid sim_dbs2_sid
                 sim_dbs1_long sim_dbs2_long
                 sim_dbs1_long_t sim_dbs2_long_t;
run;

/* Sort for mixed model analysis */
proc sort data=dat_stg1; 
    by iterID SID trt t;
run;

/*-----------------------------------------------------------------------------
 * STAGE 1: MIXED MODEL ANALYSIS
 *----------------------------------------------------------------------------*/

/* Analyze Stage 1 data using mixed effects model with AR(1) correlation */
ods output LSMEstimates=est1st1a 
           ConvergenceStatus=cs1st1a;

PROC MIXED DATA=dat_stg1;
    by iterID;
    CLASS SID trt(ref='1') t;
    MODEL chg = trt t trt*t / DDFM=KR S;  /* Kenward-Roger DF method */
    REPEATED t / SUBJECT=SID TYPE=AR(1);   /* AR(1) correlation structure */
    lsmestimate t*trt 'W04'  /* Week 4 treatment difference */
        0 0 0 1 0 0 0 0 0    /* Coefficients for treatment 0 at time 4 */
        0 0 0 -1 0 0 0 0 0   /* Coefficients for treatment 1 at time 4 */
        / divisor=1 e alpha=0.05;
RUN;

/*-----------------------------------------------------------------------------
 * INTERIM ANALYSIS: CONDITIONAL POWER CALCULATION
 *----------------------------------------------------------------------------*/

/* Merge Stage 1 results with convergence status */
data res1a;
    merge est1st1a cs1st1a;
    by iterID;
run;

/* Calculate conditional power and determine decision zones */
data res1a;
    set res1a;
    
    /* Skip non-converged models */
    if status = 1 then delete;
    
    /* Calculate sample sizes */
    TotalNst1 = 2*&nst1;      /* Total Stage 1 sample size */
    TotalNst2 = 2*&nst2;      /* Initial Stage 2 sample size */
    TotalN = TotalNst1 + TotalNst2;
    TotalNst2max = 2*&nmax;   /* Maximum Stage 2 sample size */
    TotalN2new = TotalNst2;
    
    /* Calculate information weights (square root of information fraction) */
    w1 = sqrt(TotalNst1/TotalN);
    w2 = sqrt(TotalNst2/TotalN);
    wratio = w1/w2;
    
    /* Convert t-statistic to z-statistic */
    zvalt = quantile('normal', 1 - Probt/2);
    if tValue < 0 then zValue = -zvalt;
    if tValue >= 0 then zValue = zvalt;
    
    /* Calculate conditional power using current trend */
    CondPow = 1 - probnorm(&cst2./w2 - zValue*wratio - zValue/wratio);
    CondPow2 = 1 - probnorm(&cst2./w2 - tValue*wratio - tValue/wratio);
    zCp = probit(1 - &beta.);
    
    /* Initialize decision zone flags */
    futflag = 0;  /* Futility */
    unfflag = 0;  /* Unfavorable */
    prmflag = 0;  /* Promising */
    favflag = 0;  /* Favorable */
    effflag = 0;  /* Efficacious */
    
    /* Determine decision zone based on conditional power and Stage 1 result */
    if CondPow < &cp1fut then do;
        Region = "FUTILE";
        futflag = 1;
    end;
    else if &cp1fut =< CondPow =< &cp1lowpz then do;
        Region = "UNFAVO";
        unfflag = 1;
    end;
    else if &cp1lowpz =< CondPow =< &cp2highpz then do;
        Region = "PROMIS";
        prmflag = 1;
    end;
    else if (CondPow > &cp2highpz) and (tValue > &cst1) then do;
        Region = "FAVORA";
        favflag = 1;
    end;
    else if (CondPow > &cp2highpz) and (tValue <= &cst1) then do;
        Region = "EFFICA";
        effflag = 1;
    end;
    
    /* Adjust Stage 2 sample size for promising zone */
    if Region in("PROMIS") then do;
        TotalN2new = TotalNst2max;  /* Increase to maximum */
    end;
    
    N2new = TotalN2new / 2;  /* Per-arm Stage 2 sample size */
    TotalNfinal = TotalNst1 + TotalN2new;
run;

/* Clean up and rename variables */
data res1a;
    set res1a;
    drop Label DF Probt Alpha Lower Upper Reason Status pdG pdH;
    rename Estimate = Diffst1 
           StdErr = SEst1 
           tValue = tst1 
           zvalue = zst1;
run;

/*-----------------------------------------------------------------------------
 * STAGE 2: SIMULATION AND ANALYSIS
 *----------------------------------------------------------------------------*/

/* Initialize Stage 2 dataset */
data dat_stg2;
    iterID = 0;
run;

/* Generate Stage 2 data for each iteration */
%simdatst2;

/* Remove initialization record */
data dat_stg2;
    set dat_stg2;
    if iterID = 0 then delete;
run;

/* Sort for mixed model analysis */
proc sort data=dat_stg2; 
    by iterID SID trt t;
run;

/* Analyze Stage 2 data */
ods output LSMEstimates=est1st2a 
           ConvergenceStatus=cs1st2a;

PROC MIXED DATA=dat_stg2;
    by iterID;
    CLASS SID trt(ref='1') t;
    MODEL chg = trt t trt*t / DDFM=KR S;
    REPEATED t / SUBJECT=SID TYPE=AR(1);
    lsmestimate t*trt 'W04'
        0 0 0 1 0 0 0 0 0
        0 0 0 -1 0 0 0 0 0 
        / divisor=1 e alpha=0.05;
RUN;

/* Process Stage 2 results */
data res2a;
    merge est1st2a cs1st2a;
    by iterID;
run;

data res2a;
    set res2a;
    if status = 1 then delete;
run;

data res2a;
    set res2a;
    
    /* Convert to z-statistics */
    zvalt = quantile('normal', 1 - Probt/2);
    if tValue < 0 then zValue = -zvalt;
    if tValue >= 0 then zValue = zvalt;
    
    drop Label DF Probt Alpha Lower Upper Reason Status pdG pdH;
    rename Estimate = Diffst2 
           StdErr = SEst2 
           tValue = tst2 
           zvalue = zst2;
run;

/*-----------------------------------------------------------------------------
 * FINAL ANALYSIS: COMBINE STAGES AND CALCULATE POWER
 *----------------------------------------------------------------------------*/

/* Merge Stage 1 and Stage 2 results */
data finalres;
    merge res1a res2a;
    by iterID;
run;

/* Calculate combined test statistic and final power */
data finalres;
    set finalres;
    
    /* Weighted combination of Stage 1 and Stage 2 z-statistics */
    zCHW = w1*zst1 + w2*zst2;
    
    /* Determine if trial is successful */
    power = 0;
    if zCHW > &cst2 then power = 1;
    
    /* Override based on interim decision */
    if Region in("EFFICA") then power = 1;  /* Already significant at Stage 1 */
    if Region in("FUTILE") then power = 0;  /* Stopped for futility */
run;

/*-----------------------------------------------------------------------------
 * OPERATING CHARACTERISTICS: SUMMARY STATISTICS
 *----------------------------------------------------------------------------*/

/* Sort by region for by-group processing */
proc sort data=finalres;
    by Region;
run;

/* Calculate means by decision region */
proc univariate data=finalres noprint;
    by Region;
    var TotalNfinal CondPow futflag unfflag prmflag favflag effflag Power;
    output out=sumres 
           mean=TotalNfinalavg CondPowavg futflagavg unfflagavg 
                prmflagavg favflagavg effflagavg Poweravg;
run;

/* Calculate overall means across all regions */
proc univariate data=finalres noprint;
    var TotalNfinal CondPow futflag unfflag prmflag favflag effflag Power;
    output out=sumresoverall 
           mean=TotalNfinalavg CondPowavg futflagavg unfflagavg 
                prmflagavg favflagavg effflagavg Poweravg;
run;

/* Add overall label */
data sumresoverall;
    set sumresoverall;
    Region = "Overall";
run;

/* Combine regional and overall summaries */
data oc;
    length Region $10;
    set sumres sumresoverall;
run;

/*-----------------------------------------------------------------------------
 * EXPORT RESULTS TO EXCEL
 *----------------------------------------------------------------------------*/

/* Export operating characteristics summary */
proc export data=oc 
            DBMS=xlsx 
            OUTFILE="&output_path.&outd" replace;
run;

/* Export detailed simulation results */
proc export data=finalres 
            DBMS=xlsx 
            OUTFILE="&output_path.&outd2" replace;
run;

/******************************************************************************
 * END OF PROGRAM
 * 
 * Expected Output:
 * 1. modsum_base.xlsx - Summary statistics by decision region
 *    - Average sample size, conditional power, and power by region
 *    - Proportion of simulations in each decision zone
 *    
 * 2. modOC_base.xlsx - Detailed results for each simulation
 *    - Stage 1 and Stage 2 test statistics
 *    - Conditional power calculations
 *    - Final decision and power indicator
 *    
 * Notes:
 * - Increase 'iter' to 10,000+ for production runs
 * - Monitor convergence rates in mixed models
 * - Check for sufficient variability in correlation matrices
 ******************************************************************************/