Timyd -- A networking monitoring/spying tool in Python

# Description

Timyd Is Monitoring Your Domain!

Timyd is a simple networking monitoring tool. It can be setup to regularly
check a set of services, programs or machines and record the result in binary
logs. It can then alert you if the status of a service changes, or send
daily/weekly recaps by email or other mean.

In addition to status check, Timyd is intended to be able to track and record
any kind of 'property' of a service; this allows it to provide context for
status change (eg this service broke at the same time this server software
changed version) or just random information about a domain ('spying').

Both service checks and actions are written in Python, allowing to add your own
check or custom reporting actions.
