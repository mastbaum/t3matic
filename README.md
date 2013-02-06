t3matic: Making the most of someone else's cluster
==================================================
t3matic runs rat simulations on clusters. It keeps a given number of
jobs in the system at any time, roughly in proportion to the rates
associated with user-specified signals and backgrounds.

Supported Cluster Systems:

* Condor
* Grid Engine

Features:

* "Set it and forget it" approach ensures 100% cluster usage all the time
* Run time and memory limits keep jobs from running away
* Script runs on any system with SSH access to the cluster
* Uses no local disk on the cluster
* Web-based interface for specifying configuration and simulations
* Web-based queue monitoring

