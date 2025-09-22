/******************************************************************************
 * ADAPTIVE CLINICAL TRIAL SIMULATION WITH CONDITIONAL POWER
 * 
 * Purpose: This program simulates a two-stage adaptive clinical trial design
 *          with interim analysis based on conditional power calculations.
 *          
 * Key Features:
 * - Stage 1: Initial trial with fixed sample size
 * - Interim Analysis: Conditional power calculation to determine next steps
 * - Stage 2: Continuation with potentially adapted sample size
 * - Operating Characteristics: Power, sample size, and region probabilities
 *
 * Author: Vikas Gaddu
 * Date: 2025-09-22
 * Version: 1.0 - CASL Implementation
 ******************************************************************************/

/*=============================================================================
 * SECTION 1: PROGRAM HEADER
 *============================================================================*/

/* Note: Setup parameters are now included programmatically by the Python script */

/*=============================================================================
 * SECTION 2: ENVIRONMENT-SPECIFIC SETTINGS
 * Define paths and settings specific to the CASL environment
 *============================================================================*/

/* File paths for input data and output results */
%let data_path = /xar/general/biostat/jobs/gadam_ongoing_studies/prod/programs/vgaddu/CASL/data;
%let output_path = /xar/general/biostat/jobs/gadam_ongoing_studies/prod/programs/vgaddu/CASL/output/;
%let file1 = &data_path./simdata1.csv;  /* Treatment group 0 correlation structure */
%let file2 = &data_path./simdata2.csv;  /* Treatment group 1 correlation structure */

/* Output file names specific to CASL */
%let outd = modsum_casl.xlsx;    /* Summary statistics by region */
%let outd2 = modOC_casl.xlsx;     /* Detailed simulation results */

/* Enable macro debugging */
options mprint;

/*=============================================================================
 * SECTION 3: MACRO DEFINITIONS
 *============================================================================*/

/**
 * MACRO: simulate_and_process
 * Purpose: Generate simulated multivariate normal data and transform to long format
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
                   outsim=casuser.&output_prefix
                   numreal=%sysevalf(&nst*&iter) 
                   seed=&seed;
        var y1-y10;  /* 10 time points */
    run;

    /* Step 2: Create iteration and subject identifiers */
    data casuser.&output_prefix._sid;
        set casuser.&output_prefix;
        row_num = monotonic();  /* Sequential row counter */
        iterID = floor((row_num-1) / &nst) + 1;  /* Iteration number */
        
        /* Calculate subject ID with optional offset */
        %if &sid_offset > 0 %then %do;
            SID = mod(rnum, &nst) + &sid_offset + 1;
        %end;
        %else %do;
            SID = mod(rnum, &nst) + 1;
        %end;
        
        dummy_id = 1;  /* Required for PROC TRANSPOSE in CAS */
        drop row_num rnum;
    run;

    /* Step 3: Reshape from wide to long format */
    proc transpose data=casuser.&output_prefix._sid
                   out=casuser.&output_prefix._long
                   name=_NAME_;
        by iterID SID;
        id dummy_id;
        var y1-y10;
    run;

    /* Step 4: Add time and treatment variables */
    data casuser.&output_prefix._long_t;
        set casuser.&output_prefix._long (rename=(_1=y));
        t = input(substr(_name_, 2), 2.);  /* Extract time point (1-10) */
        visit = cat("t", input(substr(_name_, 2), 2.));  /* Visit label */
        trt = &trt_value;  /* Treatment assignment */
        drop _name_;
    run;
%mend simulate_and_process;

/**
 * MACRO: start_cas_session
 * Purpose: Initialize CAS session if not already exists
 */
%macro start_cas_session;
    %if %sysfunc(sessfound(mysession)) = 0 %then %do;
        cas mysession;
        caslib _all_ assign sessref=mysession;  /* Auto-assign all CAS libraries */
        %put NOTE: Created new CAS session MYSESSION;
    %end;
    %else %do;
        %put NOTE: Using existing CAS session MYSESSION;
    %end;
%mend start_cas_session;

/**
 * MACRO: simdatst2
 * Purpose: Simulate Stage 2 data for each iteration based on Stage 1 results
 */
%macro simdatst2;
    %do icnt = 1 %to &iter;
        %let n2st2 = 0;
        
        /* Get Stage 2 sample size from Stage 1 results */
        data _null_;
            set casuser.res1a;
            if iterID = &icnt then 
                call symput('n2st2', trim(left(put(N2new, 4.))));
        run;
        
        /* Generate iteration-specific seeds */
        %let sed1 = %sysfunc(ceil(&seed12i + 10*&icnt));
        %let sed2 = %sysfunc(ceil(&seed22i + 3*&icnt));
        
        /* Simulate both treatment groups for this iteration */
        %simulate_and_process(
            input_data=simdata1c,
            output_prefix=sim_dbs1_iter&icnt,
            seed=&sed1,
            nst=&nst2,
            iter=1,
            sid_offset=0,
            trt_value=0
        );
        
        %simulate_and_process(
            input_data=simdata2c,
            output_prefix=sim_dbs2_iter&icnt,
            seed=&sed2,
            nst=&nst2,
            iter=1,
            sid_offset=&nst2,
            trt_value=1
        );
        
        /* Clean up any existing iteration table */
        proc cas;
            action table.dropTable /
                name="dat_stg2iter&icnt"
                caslib="casuser"
                quiet=true;
        run;
        
        /* Combine groups and calculate change from baseline using SQL */
        proc fedsql sessref=mysession;
            create table casuser.dat_stg2iter&icnt as
            select 
                a.SID,
                &icnt as iterID,
                a.t,
                a.trt,
                a.y,
                a.visit,
                b.y as bsl,  /* Baseline value (t=1) */
                case 
                    when a.t = 1 then null  /* No change at baseline */
                    else a.y - b.y          /* Change from baseline */
                end as chg
            from (
                /* Union both treatment groups */
                select * from casuser.sim_dbs1_iter&icnt._long_t
                union all
                select * from casuser.sim_dbs2_iter&icnt._long_t
            ) as a
            left join (
                /* Get baseline values only */
                select SID, iterID, y 
                from casuser.sim_dbs1_iter&icnt._long_t 
                where t = 1
                union all
                select SID, iterID, y 
                from casuser.sim_dbs2_iter&icnt._long_t 
                where t = 1
            ) as b
            on a.SID = b.SID and a.iterID = b.iterID;
        quit;
        
        /* Clean up intermediate datasets */
        proc cas;
            action table.dropTable / name="sim_dbs1_iter&icnt" caslib="casuser" quiet=true;
            action table.dropTable / name="sim_dbs2_iter&icnt" caslib="casuser" quiet=true;
            action table.dropTable / name="sim_dbs1_iter&icnt._sid" caslib="casuser" quiet=true;
            action table.dropTable / name="sim_dbs2_iter&icnt._sid" caslib="casuser" quiet=true;
            action table.dropTable / name="sim_dbs1_iter&icnt._long" caslib="casuser" quiet=true;
            action table.dropTable / name="sim_dbs2_iter&icnt._long" caslib="casuser" quiet=true;
            action table.dropTable / name="sim_dbs1_iter&icnt._long_t" caslib="casuser" quiet=true;
            action table.dropTable / name="sim_dbs2_iter&icnt._long_t" caslib="casuser" quiet=true;
        run;
    %end;
    
    /* Combine all iterations into single dataset */
    data casuser.dat_stg2;
        set 
        %do i = 1 %to &iter;
            casuser.dat_stg2iter&i
        %end;
        ;
    run;
    
    /* Clean up iteration-specific datasets */
    proc cas;
        %do i = 1 %to &iter;
            action table.dropTable / 
                name="dat_stg2iter&i" 
                caslib="casuser" 
                quiet=true;
        %end;
    run;
%mend simdatst2;

/*=============================================================================
 * SECTION 4: MAIN SIMULATION EXECUTION
 *============================================================================*/

/* Initialize CAS session */
%start_cas_session;

/*-----------------------------------------------------------------------------
 * STAGE 1: DATA PREPARATION AND INITIAL SIMULATION
 *----------------------------------------------------------------------------*/

/* Load correlation data from CSV files */
proc casutil;
    load file="&file1" 
         outcaslib="casuser" 
         casout="simdata1" 
         replace
         importoptions=(filetype="csv" getnames=true);
         
    load file="&file2" 
         outcaslib="casuser" 
         casout="simdata2" 
         replace
         importoptions=(filetype="csv" getnames=true);
         
    list tables incaslib="casuser";
quit;

/* Create correlation datasets for simulation */
data simdata1c(type=corr);
    set casuser.simdata1;
run;

data simdata2c(type=corr);
    set casuser.simdata2;
run;

/* Generate Stage 1 simulated data */
%simulate_and_process(
    input_data=simdata1c,
    output_prefix=sim_dbs1,
    seed=&seed11i,
    nst=&nst1,
    iter=&iter,
    sid_offset=0,
    trt_value=0
);

%simulate_and_process(
    input_data=simdata2c,
    output_prefix=sim_dbs2,
    seed=&seed21i,
    nst=&nst1,
    iter=&iter,
    sid_offset=&nst1,
    trt_value=1
);

/* Combine Stage 1 data and calculate change from baseline */
proc cas;
    action table.dropTable / 
        name="data_stg1" 
        caslib="casuser" 
        quiet=true;
run;

proc fedsql sessref=mysession noerrorstop;
    create table casuser.data_stg1 as
    select 
        a.SID,
        a.iterID,
        a.t,
        a.trt,
        a.y,
        b.y as bsl,
        case 
            when a.t = 1 then .
            else a.y - b.y
        end as chg
    from (
        select * from casuser.sim_dbs1_long_t
        union all
        select * from casuser.sim_dbs2_long_t
    ) as a
    left join (
        select SID, iterID, y 
        from casuser.sim_dbs1_long_t where t = 1
        union all
        select SID, iterID, y 
        from casuser.sim_dbs2_long_t where t = 1
    ) as b
    on a.SID = b.SID and a.iterID = b.iterID;
quit;

/* Sort data for mixed model analysis */
proc sort data=casuser.data_stg1 out=data_stg1;
    by iterID SID trt t;
run;

/*-----------------------------------------------------------------------------
 * STAGE 1: MIXED MODEL ANALYSIS
 *----------------------------------------------------------------------------*/

/* Analyze Stage 1 data using mixed effects model with AR(1) correlation */
ods output LSMEstimates=casuser.est1st1a 
           ConvergenceStatus=casuser.cs1st1a;

PROC MIXED DATA=data_stg1;
    by iterID;
    CLASS SID trt(ref='1') t;
    MODEL chg = trt t trt*t / DDFM=KR S;  /* Kenward-Roger DF */
    REPEATED t / SUBJECT=SID TYPE=AR(1);   /* AR(1) correlation structure */
    lsmestimate t*trt 'W04'  /* Week 4 treatment difference */
        0 0 0 1 0 0 0 0 0
        0 0 0 -1 0 0 0 0 0 / divisor=1 e alpha=0.05;
RUN;

/*-----------------------------------------------------------------------------
 * INTERIM ANALYSIS: CONDITIONAL POWER CALCULATION
 *----------------------------------------------------------------------------*/

/* Merge Stage 1 results */
data casuser.res1a;
    merge casuser.est1st1a casuser.cs1st1a;
    by iterID;
run;

/* Calculate conditional power and determine decision zones */
data casuser.res1a;
    set casuser.res1a;
    
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
    zCp = quantile('normal', 1 - &beta.);
    
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
data casuser.res1a;
    set casuser.res1a;
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
data casuser.dat_stg2;
    iterID = 0;
run;

/* Generate Stage 2 data for each iteration */
%simdatst2;

/* Remove initialization record */
data casuser.dat_stg2;
    set casuser.dat_stg2;
    if iterID = 0 then delete;
run;

/* Analyze Stage 2 data */
ods output LSMEstimates=casuser.est1st2a 
           ConvergenceStatus=casuser.cs1st2a;

PROC MIXED DATA=casuser.dat_stg2;
    by iterID;
    CLASS SID trt(ref='1') t;
    MODEL chg = trt t trt*t / DDFM=KR S;
    REPEATED t / SUBJECT=SID TYPE=AR(1);
    lsmestimate t*trt 'W04'
        0 0 0 1 0 0 0 0 0
        0 0 0 -1 0 0 0 0 0 / divisor=1 e alpha=0.05;
RUN;

/* Process Stage 2 results */
data casuser.res2a;
    merge casuser.est1st2a casuser.cs1st2a;
    by iterID;
run;

data casuser.res2a;
    set casuser.res2a;
    if status = 1 then delete;
    
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
data casuser.finalres;
    merge casuser.res1a casuser.res2a;
    by iterID;
run;

/* Calculate combined test statistic and final power */
data casuser.finalres;
    set casuser.finalres;
    
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


/* Calculate means by decision region */
proc univariate data=casuser.finalres noprint;
    by Region;
    var TotalNfinal CondPow futflag unfflag prmflag favflag effflag Power;
    output out=casuser.sumres 
           mean=TotalNfinalavg CondPowavg futflagavg unfflagavg 
                prmflagavg favflagavg effflagavg Poweravg;
run;

/* Calculate overall means across all regions */
proc univariate data=casuser.finalres noprint;
    var TotalNfinal CondPow futflag unfflag prmflag favflag effflag Power;
    output out=casuser.sumresoverall 
           mean=TotalNfinalavg CondPowavg futflagavg unfflagavg 
                prmflagavg favflagavg effflagavg Poweravg;
run;

/* Add overall label */
data casuser.sumresoverall;
    set casuser.sumresoverall;
    Region = "Overall";
run;

/* Combine regional and overall summaries */
data casuser.oc;
    set casuser.sumres casuser.sumresoverall;
run;

/*-----------------------------------------------------------------------------
 * EXPORT RESULTS TO EXCEL
 *----------------------------------------------------------------------------*/

/* Export operating characteristics summary */
proc export data=casuser.oc 
           DBMS=xlsx 
           OUTFILE="&output_path.&outd"
           replace;
run;

/* Export detailed simulation results */
proc export data=casuser.finalres 
           DBMS=xlsx 
           OUTFILE="&output_path.&outd2"
           replace;
run;

/******************************************************************************
 * END OF PROGRAM
 * 
 * Expected Output:
 * 1. modsum_casl.xlsx - Summary statistics by decision region
 *    - Average sample size, conditional power, and power by region
 *    - Proportion of simulations in each decision zone
 *    
 * 2. modOC_casl.xlsx - Detailed results for each simulation
 *    - Stage 1 and Stage 2 test statistics
 *    - Conditional power calculations
 *    - Final decision and power indicator
 ******************************************************************************/