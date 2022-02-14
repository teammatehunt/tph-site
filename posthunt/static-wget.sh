# Clean up old directory if it's still there.
# FIXME: change to hunt domain
rm -r mypuzzlehunt.com
# Do a recursive wget on the site
wget      --recursive      --no-clobber      --ignore-tags=img,link,script,style        --html-extension      --convert-links      --restrict-file-names=windows      --domains mypuzzlehunt.com      --no-parent          mypuzzlehunt.com
# Note: to test against localhost, you can use this command.
# wget      --recursive      --no-clobber      --page-requisites      --html-extension      --convert-links      --restrict-file-names=windows      --domains localhost      --no-parent          http://localhost:8081 --no-check-certificate
# This will save it to directory localhost+8081
