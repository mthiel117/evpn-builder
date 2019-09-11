import yaml
import requests
import json
from cvplibrary import CVPGlobalVariables, GlobalVariableNames
from cvplibrary import Device

#Revision 0.4

device_ip = CVPGlobalVariables.getValue(GlobalVariableNames.CVP_IP)
dev_user = CVPGlobalVariables.getValue(GlobalVariableNames.CVP_USERNAME)
dev_pass = CVPGlobalVariables.getValue(GlobalVariableNames.CVP_PASSWORD)

def authenticate():
  #Send username and password via API and get session ID in cookies in order to use for future API calls.
  
  #Login API Url
  authUrl = "https://localhost/web/login/authenticate.do"
  
  #Create JSON object with username and password.
  authPayload = '''{
    "userId": \"%s\",
    "password": \"%s\"
    }''' % (dev_user, dev_pass)
    
  #Establish connection headers                  
  headers = {
      'Content-Type': "application/json",
      'cache-control': "no-cache",
      }
  
  #Perform API call for authentication and log response as a variable.
  response = requests.request("POST", authUrl, data=authPayload, headers=headers, verify=False)
  
  #Pull coookies out of response that contains session ID.
  connectionCookies = response.cookies
  
  #Return cookies to main for use with other functions.
  return(connectionCookies)

def buildEvpn(connectionCookies):
  #Get Device name and IP for SVIs based on Device Hostname
  deviceCollect = getDeviceNAMEID()
  device_name = deviceCollect[0]
  svi_ip = deviceCollect[1]
  #Get Router ID and local BGP ASN
  deviceInfo = getDeviceRTRID()
  deviceRtrID = deviceInfo[0]
  bgp_as = deviceInfo[1]
  #Create VRF List
  vrfList = []
  #Create Vlan Dictionary
  vlanDict = {}
  #Route Target Dictionary
  tarDict = {}

  #Get vlans from a specified configlet that will be in YAML format.
  
    #Get Configlet API URL
  url = "https://localhost/cvpservice/configlet/getConfigletByName.do"
  
  #Establish connection headers
  headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
      }
  
  #Query string to specify the name of the configlet.
  querystring = {"name":"EVPN-vlansv2.yml"}
  
  #Perform API call to get the configlet by name based on the URL and Query String and save response to a
  #variable.
  response = requests.request("GET", url, cookies=connectionCookies, headers=headers, params=querystring, verify=False)
  
  #Load the JSON object from the 'config' output in the response, read it as YAML, and save it to a variable
  deviceInfo = yaml.safe_load(json.loads(response.text)['config'])

#Loop through VRFs and print out the name of each VRF
  if "spine" in device_name:
    pass
  else:
    for device in deviceInfo['devices']:
      if device['deviceName'] == device_name:
        for v1 in device['appliedVlans']:
          for vxlan in deviceInfo['vlans']:
            if str(vxlan['vlanId']) == str(v1):
              for vrf in deviceInfo['vrfs']:
                if vrf['vrfName'] == vxlan['vrfDef']:
                  if vrf['vrfName'] not in vrfList:
                    vrfList.append(vrf['vrfName'])
    #print vrfList based on applied vlans
    for vrfIn in vrfList:
      print('vrf definition ' + vrfIn)
      print('ip routing vrf ' + vrfIn)
    print "!"
    #build vxlan interface based on applied vlans
    print "interface vxlan1"
    for device in deviceInfo['devices']:
      if device['deviceName'] == device_name:
        for v2 in device['appliedVlans']:
          for vxlan in deviceInfo['vlans']:
            if str(vxlan['vlanId']) == str(v2):
              print ('vxlan vlan ' + str(vxlan['vlanId']) + ' vni ' + vxlan['vlanVni'])
    #build IRB vni's based on applied vlans
    for vrf in deviceInfo['vrfs']:
      for vrfIn in vrfList:
        if vrfIn == vrf['vrfName']:
          print ('vxlan vrf ' + vrf['vrfName'] + ' vni '+ vrf['vrfVni'])
          tarDict[vrf['vrfName']] = vrf['routeTarget']
    print "!"

#Loop through DEVICEs and print vlan and SVI
  if "spine" in device_name:
    pass
  else:
    for device in deviceInfo['devices']:
      if device['deviceName'] == device_name:
        for v1 in device['appliedVlans']:
          for vlan in deviceInfo['vlans']:
            if str(vlan['vlanId']) == str(v1):
              print('vlan ' + str(vlan['vlanId']))
              print('name ' + vlan['name'])
              print "!"
              print('interface vlan ' + str(vlan['vlanId']))
              print "no autostate"
              print('vrf forwarding ' + vlan['vrfDef'])
              print('ip address virtual ' + vlan['subnet'][:-1] + '1')
              print "!"
    
#Create base router bgp section based on device name
  if "spine" in device_name:
    if device_name.startswith('dc1-'):
      print "router bgp 65001"
      print "bgp listen range 10.0.0.0/8 peer-group IPv4-UNDERLAY-PEERS peer-filter LEAF-AS-RANGE"
      print "bgp listen range 1.1.1.0/24 peer-group EVPN-OVERLAY-PEERS peer-filter LEAF-AS-RANGE"
    else:
      print "router bgp 65002"
      print "bgp listen range 10.0.0.0/8 peer-group IPv4-UNDERLAY-PEERS peer-filter LEAF-AS-RANGE"
      print "bgp listen range 2.2.2.0/24 peer-group EVPN-OVERLAY-PEERS peer-filter LEAF-AS-RANGE"
    print "update wait-for-convergence"
    print "update wait-install"
    print "no bgp default ipv4-unicast"
    print "neighbor IPv4-UNDERLAY-PEERS peer-group"
    print "neighbor IPv4-UNDERLAY-PEERS password @rista123"
    print "neighbor IPv4-UNDERLAY-PEERS send-community"
    print "neighbor IPv4-UNDERLAY-PEERS maximum-routes 0"
    print "neighbor EVPN-OVERLAY-PEERS peer-group"
    print "neighbor EVPN-OVERLAY-PEERS next-hop-unchanged"
    print "neighbor EVPN-OVERLAY-PEERS update-source Loopback0"
    print "neighbor EVPN-OVERLAY-PEERS ebgp-multihop 3"
    print "neighbor EVPN-OVERLAY-PEERS password @rista123"
    print "neighbor EVPN-OVERLAY-PEERS send-community"
    print "neighbor EVPN-OVERLAY-PEERS maximum-routes 0"
    print "!"
    print "address-family ipv4"
    print "neighbor IPv4-UNDERLAY-PEERS activate"
    print "!"
    print "address-family evpn"
    print "neighbor EVPN-OVERLAY-PEERS activate"
  else:
    print "router bgp " + bgp_as
    print "neighbor IPv4-UNDERLAY-PEERS peer-group"
    if device_name.startswith('dc1-'):
      print "neighbor IPv4-UNDERLAY-PEERS remote-as 65001"
    else:
      print "neighbor IPv4-UNDERLAY-PEERS remote-as 65002"
    print "update wait-install"
    print "no bgp default ipv4-unicast"
    print "neighbor IPv4-UNDERLAY-PEERS password @rista123"
    print "neighbor IPv4-UNDERLAY-PEERS send-community"
    print "neighbor IPv4-UNDERLAY-PEERS maximum-routes 12000"
    print "neighbor MLAG-IPv4-UNDERLAY-PEER peer-group"
    print "neighbor MLAG-IPv4-UNDERLAY-PEER remote-as " + bgp_as
    print "neighbor MLAG-IPv4-UNDERLAY-PEER next-hop-self"
    print "neighbor MLAG-IPv4-UNDERLAY-PEER fall-over bfd"
    print "neighbor MLAG-IPv4-UNDERLAY-PEER password @rista123"
    print "neighbor MLAG-IPv4-UNDERLAY-PEER send-community"
    print "neighbor MLAG-IPv4-UNDERLAY-PEER maximum-routes 12000"
    print "neighbor EVPN-OVERLAY-PEERS peer-group"
    if device_name.startswith('dc1-'):
      print "neighbor EVPN-OVERLAY-PEERS remote-as 65001"
    else:
      print "neighbor EVPN-OVERLAY-PEERS remote-as 65002"
    print "neighbor EVPN-OVERLAY-PEERS update-source Loopback0"
    print "neighbor EVPN-OVERLAY-PEERS ebgp-multihop 3"
    print "neighbor EVPN-OVERLAY-PEERS password @rista123"
    print "neighbor EVPN-OVERLAY-PEERS send-community"
    print "neighbor EVPN-OVERLAY-PEERS maximum-routes 12000"
    if device_name.startswith('dc1-'):
      print "neighbor 10.100.10.1 peer-group EVPN-OVERLAY-PEERS"
      print "neighbor 10.100.10.2 peer-group EVPN-OVERLAY-PEERS"
    else:
      print "neighbor 10.200.10.1 peer-group EVPN-OVERLAY-PEERS"
      print "neighbor 10.200.10.2 peer-group EVPN-OVERLAY-PEERS"
  print "!"

#Create bgp vlan groups
  if "spine" in device_name:
    pass
  else:
    for device in deviceInfo['devices']:
      if device['deviceName'] == device_name:
        for v3 in device['appliedVlans']:
          for vxlan in deviceInfo['vlans']:
            if str(vxlan['vlanId']) == str(v3):
              for vrf in deviceInfo['vrfs']:
                if vrf['vrfName'] == vxlan['vrfDef']:
                  if vrf['vrfName'] not in vlanDict:
                    vlanDict[vrf['vrfName']] = str(v3)
                  else:
                    vlanDict[vrf['vrfName']] = vlanDict[vrf['vrfName']] + "," + str(v3)

#Create vlan aware bundles based newly built vlan dictionary
    for tenant, vlanGroup in vlanDict.items():
      for vrf in deviceInfo['vrfs']:
        if vrf['vrfName'] == tenant:
          print "vlan-aware-bundle TENANT-" + tenant
          print "rd " + deviceRtrID + ":" + (tarDict[vrf['vrfName']][-1])
          print "route-target both " + tarDict[vrf['vrfName']]
          print "redistribute learned"
          print "vlan " + vlanGroup
          print "!"

#Create and config the EVPN address family
    print "address-family evpn"
    print "neighbor EVPN-OVERLAY-PEERS activate"
    print "!"

#Create bgp tenants for each vrf
    for tenant, vlanGroup in vlanDict.items():
      for vrf in deviceInfo['vrfs']:
        if vrf['vrfName'] == tenant:
          print "vrf " + tenant
          print "rd " + deviceRtrID + ":" + (tarDict[vrf['vrfName']][-1])
          print "route-target import evpn " + tarDict[vrf['vrfName']]
          print "route-target export evpn " + tarDict[vrf['vrfName']]
          print "redistribute connected"
          print "!"

def getDeviceNAMEID():
  #Get device name to determine SVI IP
  cmdList = ['show hostname']
  device = Device(device_ip,dev_user,dev_pass)

  dict_resp = device.runCmds(cmdList)
  device_hostname = dict_resp[0]['response']['hostname']
  svi_id = "2"
  if device_hostname.endswith('2'):
    svi_id = "3"
  return device_hostname, svi_id

def getDeviceRTRID():
  #Get device name to determine Device BGP AS
  cmdList = ['show ip bgp summary']
  device = Device(device_ip,dev_user,dev_pass)

  dict_resp = device.runCmds(cmdList)
  device_rtrid = dict_resp[0]['response']['vrfs']['default']['routerId']
  device_as = dict_resp[0]['response']['vrfs']['default']['asn']
  return device_rtrid, device_as

def main():
  #Main function
  connectionCookies = authenticate()
  buildEvpn(connectionCookies)
  
if __name__ == '__main__':
    main()
    
