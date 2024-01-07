============
Features
============

This document describes the features of Rodhaj and an general description on them.

User Features
=============

These are the publicly available features that an user can use.

Closing
-------

Naturally as communications come to an end, users cannot simply leave the ticket stale.
In order to close a ticket, it is recommended to use the ``?close`` command.
The ticket will be marked as closed to the user and subsequently closed on the ticket pool.
Once closed, a ticket cannot be reopened. If a staff uses the ``?close`` command,
the active ticket will be closed and the user will be notified of the closure.

Note that there is no plans to support timed closures, 
as it is a design feature fudmentally flawed for this type of command.

Administrative Features
=======================

Replying
--------

In order to reply to a thread, use the ``?reply`` command. 
This will send a message to the user within an active ticket.
Without executing this command, all messages will be seen as internal in the ticket. 
Images attachments, emojis, and stickers are supported.

.. note::

    Unlike ModMail, **none** of the messages sent with the ``?reply`` command, internally in the ticket, 
    or by the user to staff will be logged. This is to ensure that the privacy of the user is respected. 
    Staff can always look back at an closed ticket within the ticket channel if they need to refer 
    to a particular message.

Tags
----

To aid with frequent responses, tags can be used. Tags do not have an owner associated, thus they can be used and edited by any staff member.
Tags can be used by using the ``?tag <tag name>`` command, where ``<tag name>`` represents the name of the tag that should be used.
By default, they are sent directly to the user who is in the ticket, but can be sent internally by using the ``--ns`` flag.
