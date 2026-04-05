export GERRIT_CHANGE_ID=100
export GERRIT_PATCHSET_NUMBER=99
echo python -m dci trigger --config  dci/conf/conf_ci_trigger.json 
python -m dci trigger --config  dci/conf/conf_ci_trigger.json 