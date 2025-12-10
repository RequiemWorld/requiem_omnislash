# Purpose of Omnislash

The purpose of this library is to provide an enhancement layer/separate automation layer on top of Pulumi to allow for more control over the lifecycle of components, and to provide helper code for commons tasks pulumi doesn't. [I raised an issue about the limitations of the Pulumi lifecycle](https://github.com/pulumi/pulumi/issues/20619) which make it impossible to verify that a newly created server is correctly setup prior to deleting the old one, I advise reading it as a primer for this. 

