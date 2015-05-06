#!/bin/bash

SCRIPT_FOLDER=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
OUTPUT_FILE=$1
shift
INPUT_FILES=$@

if [[ $# -eq 0 ]] ; then
  echo 'No PDF input files'
  exit 0
fi

cmyk_profile="$SCRIPT_FOLDER/ISOnewspaper26v4.icc"
rgb_profile="$SCRIPT_FOLDER/sRGB.icc"


# Compile pdf files into multipage document.
/usr/bin/gs \
  -sDefaultCMYKProfile=$cmyk_profile \
  -sDefaultRGBProfile=$rgb_profile \
  -dProcessColorModel=/DeviceRGB \
  -dColorConversionStrategyForImages=/DeviceRGB \
  -dCompatibilityLevel=1.4 \
  -dBATCH  \
  -dNOPAUSE  \
  -sDEVICE=pdfwrite  \
  -dFastWebView=true \
  -dConvertCMYKImagesToRGB=true \
  -dDownsampleColorImages=true \
  -dDownsampleGrayImages=true \
  -dDownsampleMonoImages=true \
  -dColorImageResolution=120 \
  -dGrayImageResolution=120 \
  -dMonoImageResolution=120 \
  -sOutputFile="$OUTPUT_FILE" \
   $INPUT_FILES

# /usr/bin/gs \
#   -sDefaultCMYKProfile=$cmyk_profile \
#   -sDEVICE=pdfwrite \
#   -dBATCH  \
#   -dNOPAUSE  \
#   -dPDFSETTINGS=/screen \
#   -sOutputFile="$OUTPUT_FILE" \
#    $INPUT_FILES