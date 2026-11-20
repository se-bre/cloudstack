// Licensed to the Apache Software Foundation (ASF) under one
// or more contributor license agreements.  See the NOTICE file
// distributed with this work for additional information
// regarding copyright ownership.  The ASF licenses this file
// to you under the Apache License, Version 2.0 (the
// "License"); you may not use this file except in compliance
// with the License.  You may obtain a copy of the License at
//
//   http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing,
// software distributed under the License is distributed on an
// "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
// KIND, either express or implied.  See the License for the
// specific language governing permissions and limitations
// under the License.
package org.apache.cloudstack.api.command.user.vm;

import org.apache.cloudstack.api.APICommand;
import org.apache.cloudstack.api.ApiConstants;
import org.apache.cloudstack.api.BaseCmd;
import org.apache.cloudstack.api.Parameter;
import org.apache.cloudstack.api.response.NicSecondaryIpResponse;
import org.apache.cloudstack.context.CallContext;

import com.cloud.user.Account;
import com.cloud.vm.NicSecondaryIp;

@APICommand(name = "addHostnameToNicSecondaryIp", description = "Adds a hostname to a NIC secondary IP. The hostname is published on the virtual router like the hostname of the NIC's primary IP.",
        responseObject = NicSecondaryIpResponse.class, requestHasSensitiveInfo = false, responseHasSensitiveInfo = false, since = "24.0.0")
public class AddHostnameToNicSecondaryIpCmd extends BaseCmd {

    @Parameter(name = ApiConstants.ID, type = CommandType.UUID, entityType = NicSecondaryIpResponse.class, required = true, description = "The ID of the NIC secondary IP address")
    private Long id;

    @Parameter(name = ApiConstants.HOST_NAME, type = CommandType.STRING, required = true, description = "The hostname (RFC 1123 hostname or FQDN) to add. It must not be in use by another Instance or secondary IP in the network", length = 253)
    private String hostname;

    @Override
    public long getEntityOwnerId() {
        Account caller = CallContext.current().getCallingAccount();
        return caller.getAccountId();
    }

    @Override
    public void execute() {
        NicSecondaryIp result = _networkService.addNicSecondaryIpHostname(id, hostname);
        NicSecondaryIpResponse response = _responseGenerator.createSecondaryIPToNicResponse(result);
        response.setResponseName(getCommandName());
        setResponseObject(response);
    }
}
