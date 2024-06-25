#!/bin/bash

# Set output messages in ublox evk-f9p
# This changes the setting in flash memory so should only need to be run once
ubxtool -P 27.31 -z CFG-MSGOUT-UBX_RXM_RAWX_USB,1
ubxtool -P 27.31 -g CFG-MSGOUT-UBX_RXM_RAWX_USB,2 | grep -A 4 'UBX-CFG-VALGET:'

ubxtool -P 27.31 -z CFG-MSGOUT-UBX_RXM_SFRBX_USB,1
ubxtool -P 27.31 -g CFG-MSGOUT-UBX_RXM_SFRBX_USB,2 | grep -A 4 'UBX-CFG-VALGET:'

ubxtool -P 27.31 -z CFG-MSGOUT-UBX_NAV_PVT_USB,1
ubxtool -P 27.31 -g CFG-MSGOUT-UBX_NAV_PVT_USB,2 | grep 'UBX-CFG-VALGET:' -A 4

ubxtool -P 27.31 -z CFG-MSGOUT-UBX_NAV_POSECEF_USB,1
ubxtool -P 27.31 -g CFG-MSGOUT-UBX_NAV_POSECEF_USB,2 | grep -A 4 'UBX-CFG-VALGET:'

ubxtool -P 27.31 -z CFG-MSGOUT-UBX_NAV_VELECEF_USB,1
ubxtool -P 27.31 -g CFG-MSGOUT-UBX_NAV_VELECEF_USB,2 | grep -A 4 'UBX-CFG-VALGET:'

ubxtool -P 27.31 -z CFG-MSGOUT-UBX_NAV_SAT_USB,1
ubxtool -P 27.31 -g CFG-MSGOUT-UBX_NAV_SAT_USB,2 | grep -A 4 'UBX-CFG-VALGET:'

ubxtool -P 27.31 -z CFG-MSGOUT-UBX_NAV_DOP_USB,1
ubxtool -P 27.31 -g CFG-MSGOUT-UBX_NAV_DOP_USB,2 | grep -A 4 'UBX-CFG-VALGET:'

ubxtool -P 27.31 -z CFG-MSGOUT-UBX_NAV_TIMEGPS_USB,1
ubxtool -P 27.31 -g CFG-MSGOUT-UBX_NAV_TIMEGPS_USB,2 | grep -A 4 'UBX-CFG-VALGET:'

ubxtool -P 27.31 -z CFG-MSGOUT-UBX_NAV_EOE_USB,1
ubxtool -P 27.31 -g CFG-MSGOUT-UBX_NAV_EOE_USB,2 | grep -A 4 'UBX-CFG-VALGET:'

