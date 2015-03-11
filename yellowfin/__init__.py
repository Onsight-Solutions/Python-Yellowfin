#!/usr/bin/env python
from base64 import b64encode
from dicttoxml import dicttoxml
from suds.client import Client
from logging import getLogger



class Yellowfin(object):
    def __init__(self, server,
                 username="admin@yellowfin.com.au", password="test"):

        self.yellowfin_server = server
        self.username = username
        self.password = password

        # Defaults
        self.master_org = None  # set this if you use client organisations
        self.secure = True  # We Default to use SSL.
        self.user_url = self.yellowfin_server
        self.admin_wsdl = 'webservices/LegacyAdministrationService?wsdl'
        self.report_wsdl = 'webservices/LegacyReportService?wsdl'
        self.logger = getLogger('yellowfin')

        # if self.secure:
        #     self.logger.warn("Make sure Yellowfin listerns to SSL.")

    @property
    def admin_client(self):
        """ The webservice client for Admin calls. """
        return Client(self.admin_url, cache=None, faults=False)

    @property
    def service_client(self):
        """ The webservice client for Service calls. """
        return Client(self.service_url, cache=None, faults=False)

    @property
    def prefix(self):
        """ The prefix used to the Hypertext Transfer Protocol """
        if self.secure:
            return 'https'
        return 'http'

    @property
    def admin_url(self):
        """ The url for the admin-wsdl """
        return '%s://%s/%s' % (self.prefix, self.admin_wsdl,
                               self.yellowfin_server)

    @property
    def service_url(self):
        """ The url for the service-wsdl """
        return '%s://%s/%s' % (self.prefix, self.report_wsdl,
                               self.yellowfin_server)

    def get_admin_service_request(self):
        asr = self.admin_client.factory.create('administrationServiceRequest')
        asr.loginId = self.username
        asr.password = self.password
        asr.orgId = '1'
        return asr

    def get_report_service_request(self):
        rsr = self.admin_client.factory.create('reportServiceRequest')
        return rsr

    def get_person(self, userid, password=None):
        person = self.admin_client.factory.create('administrationPerson')
        person.userId = userid
        if password is not None:
            person.password = password

        return person

    def get_client(self, ref_id):
        client = self.admin_client.factory.create('administrationClientOrg')
        client.clientReferenceId = ref_id
        return client

    def create_ws_group(self, name, description):
        group = self.admin_client.factory.create('administrationGroup')
        group.groupName = name
        group.groupDescription = description
        return group

    def make_call(self, client, call):
        """ Makes a call to the webservice and results a dict """
        result = client.service.remoteAdministrationCall(call)

        if result[1].statusCode == "FAILURE":
            error = dict()
            error['HTTP_CODE'] = result[0]
            error['YELLOWFIN_CODE'] = result[1].errorCode
            error['STATUS_CODE'] = result[1].statusCode
            raise UserWarning(error)
        return result[1]

    def login_get_url(self, username, password=None, orgref=None, params=None):
        orgref = self.fix_client_ref(orgref)
        session = self.login_user(username, password, orgref, params)
        return '%s/logon.i4?LoginWebserviceId=%s' % (self.user_url,
                                                     session.loginSessionId)

    def login_user(self, username, password=None, orgref=None, params=None):
        asr = self.get_admin_service_request()
        asr.person = self.get_person(username, password)
        orgref = self.fix_client_ref(orgref)
        if password is None:
            self.logger.info('Loggining in %s (%s) without a password.' %
                             (username, orgref))
            asr.function = "LOGINUSERNOPASSWORD"
            asr.orgRef = orgref
            if params is not None:
                self.logger.info("Params are ommited for login w/o a password.")
        else:
            if params is not None:
                asr.parameters = params
            asr.function = "LOGINUSER"
        return self.make_call(self.admin_client, asr)

    def logoff_user(self, sessionid):
        asr = self.get_admin_service_request()
        asr.function = "LOGOUTUSER"
        asr.loginSessionId = sessionid
        return self.make_call(self.admin_client, asr)

    def create_user(self, username, password, role="YFADMIN", firstname=None,
                    lastname=None, initial=None, salutationcode=None,
                    email=None, default_clientcode=None):
        person = self.get_person(username, password)
        person.roleCode = role
        person.firstName = firstname
        person.lastName = lastname
        person.salutationCode = salutationcode
        person.emailAddress = email

        asr = self.get_admin_service_request()

        if default_clientcode is not None:
            asr.orgRef = default_clientcode

        asr.function = "ADDUSER"
        asr.person = person
        return self.make_call(self.admin_client, asr)

    def delete_user(self, username):
        asr = self.get_admin_service_request()
        asr.function = "DELETEUSER"
        asr.person = self.get_person(username)
        return self.make_call(self.admin_client, asr)

    def update_user(self, username, role="YFADMIN", firstname=None,
                    lastname=None, initial=None, salutationcode=None,
                    email=None, default_clientcode=None):
        person = self.get_person(username)
        person.roleCode = role
        person.initial = initial
        person.firstName = firstname
        person.lastName = lastname
        person.salutationCode = salutationcode
        person.emailAddress = email

        asr = self.get_admin_service_request()
        asr.person = person
        asr.function = "UPDATEUSER"
        return self.make_call(self.admin_client, asr)

    def validate_user(self, username):
        asr = self.get_admin_service_request()
        asr.function = "VALIDATEUSER"
        asr.person = self.get_person(username)
        return self.make_call(self.admin_client, asr)

    def create_or_update_user(self, username, password, role="YFADMIN",
                              firstname=None, lastname=None, initial=None,
                              salutationcode=None, email=None,
                              default_org=None):
        default_org = self.fix_client_ref(default_org)
        try:

            # user = self.validate_user(username)
            user = self.update_user(username, role, firstname, lastname,
                                    initial, salutationcode, email)
        except UserWarning:
            user = self.create_user(username, password, role, firstname,
                                    lastname, initial, salutationcode, email,
                                    default_org)
        return user

    def change_password(self, username, new_password):
        asr = self.get_admin_service_request()
        asr.function = "CHANGEPASSWORD"
        asr.person = self.get_person(username, new_password)
        return self.make_call(self.admin_client, asr)

    def list_roles(self):
        asr = self.get_admin_service_request()
        asr.function = "LISTROLES"
        return self.make_call(self.admin_client, asr)

    def list_groups(self):
        asr = self.get_admin_service_request()
        asr.function = "LISTGROUPS"
        return self.make_call(self.admin_client, asr)

    def get_group(self, group_name, orgref):
        asr = self.get_admin_service_request()
        asr.function = "GETGROUP"
        orgref = self.fix_client_ref(orgref)
        asr.orgRef = orgref
        asr.group.groupName = group_name
        return self.make_call(self.admin_client, asr).group

    def create_group(self, group_name, orgref):
        asr = self.get_admin_service_request()
        asr.function = "CREATEGROUP"
        orgref = self.fix_client_ref(orgref)
        asr.orgRef = orgref
        asr.group = self.create_ws_group(group_name,
                                         'Group auto-created with API')
        return self.make_call(self.admin_client, asr)

    def add_user_to_group(self, username, group, orgref):
        asr = self.get_admin_service_request()
        asr.function = "INCLUDEUSERINGROUP"
        asr.group = self.get_group(group, orgref)
        asr.person = self.get_person(username)
        asr.orgRef = orgref
        return self.make_call(self.admin_client, asr)

    def remove_user_from_group(self, username, group, orgref):
        asr = self.get_admin_service_request()
        asr.function = "DELUSERFROMGROUP"
        orgref = self.fix_client_ref(orgref)
        asr.group = self.get_group(group, orgref)
        asr.person = self.get_person(username)
        asr.orgRef = orgref
        return self.make_call(self.admin_client, asr)

    def create_client_organisation(self, name, ref_id, timezone, default=False):
        if ref_id == self.master_org:
            self.logger.error("The RefId is the same as the "
                              "Master Organisation, Yellowfin has a bug that "
                              "causes the creation of the  client org anyway. "
                              "You do not want this")
            return
        asr = self.get_admin_service_request()
        asr.function = "CREATECLIENT"
        asr.client = self.get_client(ref_id)
        asr.client.clientName = name
        asr.client.timeZoneCode = timezone
        asr.client.defaultOrg = default
        return self.make_call(self.admin_client, asr)

    def delete_client_organisation(self, client_ref):
        asr = self.get_admin_service_request()
        asr.function = "DELETECLIENT"
        client_ref = self.fix_client_ref(client_ref)
        asr.client = self.get_client(client_ref)
        return self.make_call(self.admin_client, asr)

    def add_user_to_client_organisation(self, userid, client_ref):
        asr = self.get_admin_service_request()
        asr.function = "ADDUSERACCESS"
        asr.client = self.get_client(client_ref)
        asr.person = self.get_person(userid)
        return self.make_call(self.admin_client, asr)

    def remove_user_from_client_organisation(self, userid, client_ref):
        asr = self.get_admin_service_request()
        asr.function = "REMOVEUSERACCESS"
        # client_ref = self.fix_client_ref(client_ref)
        asr.client = self.get_client(client_ref)
        asr.person = self.get_person(userid)
        return self.make_call(self.admin_client, asr)

    def fix_client_ref(self, ref):
        if ref == self.master_org:
            ref = None
        return ref

    def import_content(self, xml_or_dict, update):
        asr = self.get_admin_service_request()
        xml = xml_or_dict
        asr.function = "IMPORTCONTENT"

        if isinstance(xml, dict):
            xml = dicttoxml(xml, attr_type=False)

        if update:
            self.logger.info("Updating instead of creating.")
            asr.importOptions = list()
            asr.importOptions.append({"itemIndex": "0",
                                      "optionKey": "OPTION",
                                      "optionValue": "IMPORT"})

            asr.importOptions.append({"itemIndex": "1",
                                      "optionKey": "OPTION",
                                      "optionValue": "REPLACE"})

        asr.parameters = b64encode(xml)

        return self.make_call(self.admin_client, asr)

    def errorcode_to_string(self, error_code):
        """ Convert the error code received from Yellowfin to a string. """
        error_code_dict = dict()
        error_code_dict[str(-2)] = 'Unknown Error'
        error_code_dict[str(-1)] = 'Cannot Connect'
        error_code_dict[str(0)] = 'No Error'
        error_code_dict[str(1)] = 'User Not Authenticated'
        error_code_dict[str(2)] = 'No webservice Access'
        error_code_dict[str(3)] = 'Person Required'
        error_code_dict[str(4)] = 'Could Not Create Person'
        error_code_dict[str(5)] = 'Could not Reload License'
        error_code_dict[str(6)] = 'Login already in use'
        error_code_dict[str(7)] = 'Could not Delete Person'
        error_code_dict[str(8)] = 'Could not Find Person'
        error_code_dict[str(9)] = 'License Breach'
        error_code_dict[str(10)] = 'Could not Load Report Access'
        error_code_dict[str(11)] = 'Could not Load Report List'
        error_code_dict[str(12)] = 'Could not Find Group'
        error_code_dict[str(13)] = 'Group Exists'
        error_code_dict[str(14)] = 'Birt Object Null'
        error_code_dict[str(15)] = 'Birt Object No Data'
        error_code_dict[str(16)] = 'Birt Object Source Missing'
        error_code_dict[str(17)] = 'Birt Could Not Save'
        error_code_dict[str(18)] = 'Birt Could Not Save Birt File'
        error_code_dict[str(19)] = 'Could not update password'
        error_code_dict[str(20)] = 'Unknown webservice function'
        error_code_dict[str(21)] = 'Invalid client reference'
        error_code_dict[str(22)] = 'Client exists'
        error_code_dict[str(23)] = 'Could not find report'
        error_code_dict[str(24)] = 'Report is draft'
        error_code_dict[str(25)] = 'Could not authenticate user'
        error_code_dict[str(26)] = 'Unsecure logon not enabled'
        error_code_dict[str(27)] = 'Role not found'
        error_code_dict[str(28)] = 'Could not load favourites'
        error_code_dict[str(29)] = 'Reponse is too large'
        error_code_dict[str(30)] = 'Source not found'
        error_code_dict[str(31)] = 'Empty recipient list'
        error_code_dict[str(32)] = 'Broadcast failed'
        error_code_dict[str(33)] = 'Filter values failed'
        error_code_dict[str(34)] = 'Client orgs disabled'
        error_code_dict[str(35)] = 'Dashboard tab not found'
        error_code_dict[str(36)] = 'Schedule null'
        error_code_dict[str(37)] = 'Unknown status code'
        error_code_dict[str(38)] = 'Password requirements not met'
        error_code_dict[str(39)] = 'Login maximum attempts'
        error_code_dict[str(42)] = 'Import version not compatible'
        error_code_dict[str(48)] = 'Email address already in use'

        try:
            error_text = error_code_dict[str(error_code)]
        except KeyError:
            error_text = 'Unknown'
            self.logger.info("Unknown Error code: %d" % error_code)
        return error_text

