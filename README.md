t3matic: Making the most of someone else's cluster
==================================================
t3matic runs rat simulations on a Condor cluster. it keeps a given number of
jobs in the system at any time, roughly in proportion to the rates
associated with user-specified signals and backgrounds.

Features:

* "Set it and forget it" approach ensures 100% cluster usage all the time
* Run time and memory limits keep jobs from running away
* Script runs on any system with SSH access to the Condor host
* Uses no local disk on the Condor cluster
* Web-based interface for specifying configuration and simulations
* Web-based queue monitoring

