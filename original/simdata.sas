
%macro simdata(nstg,dbs1,dbs2,noutp,itrn,sed1i,sed2i);

proc simnormal data=&dbs1 outsim=sim_dbs1
			   numreal = %sysevalf(&nstg*&itrn) 
               seed = &sed1i;         
   var y1-y10;
run;
 
data sim_dbs1;
set sim_dbs1;
iterID = floor((_N_-1) / &nstg) + 1; 
SID = mod(rnum,&nstg) + 1;
drop rnum; 
run;

proc sort data = sim_dbs1;
by iterID SID;
run;

proc transpose data=sim_dbs1 out=sim_dbs1_long;
   by iterID SID ;
run;

data sim_dbs1_long_t;
  set sim_dbs1_long (rename=(col1=y));
  t=input(substr(_name_, 2), 2.);
  visit=cat("t",input(substr(_name_, 2), 2.));
  trt = 0;
  drop _name_;
run; 


proc simnormal data=&dbs2 outsim=sim_dbs2
			   numreal = %sysevalf(&nstg*&itrn) 
               seed = &sed2i;         
   var y1-y10;
run;

data sim_dbs2;
set sim_dbs2;
iterID = floor((_N_-1) / &nstg) + 1;   
SID = mod(rnum,&nstg) +  &nstg + 1;
drop rnum; 
run;

proc sort data = sim_dbs2;
by iterID SID;
run;

proc transpose data=sim_dbs2 out=sim_dbs2_long;
   by iterID SID;
run;

data sim_dbs2_long_t;
  set sim_dbs2_long (rename=(col1=y));
  t=input(substr(_name_, 2), 2.);
  visit=cat("t",input(substr(_name_, 2), 2.));
  trt = 1;
  drop _name_;
run; 

data sim_dbs_long_t_comb;
set sim_dbs1_long_t sim_dbs2_long_t;
run;

data sim_dbs_long_t_bsl;
set sim_dbs_long_t_comb;
if t=1;
rename y=bsl;
run;

proc sort data = sim_dbs_long_t_comb;
by SID iterID;
run;

proc sort data = sim_dbs_long_t_bsl;
by SID iterID;
run;

data sim_dbs_long_t_comb_bsl;
merge  sim_dbs_long_t_comb sim_dbs_long_t_bsl;
by SID iterID;
run;

data &noutp;
set sim_dbs_long_t_comb_bsl;
chg = y-bsl;
if t = 1 then chg = .;
run;

proc sort data = &noutp;
by iterID SID ;
run;

proc delete data = sim_dbs1 sim_dbs2  sim_dbs1_long sim_dbs2_long  sim_dbs1_long_t sim_dbs2_long_t sim_dbs_long_t_comb_bsl sim_dbs_long_t_comb sim_dbs_long_t_bsl; 
run;

%mend;
