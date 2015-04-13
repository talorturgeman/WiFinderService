using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Runtime.Serialization;
using System.ServiceModel;
using System.ServiceModel.Web;
using System.Text;

namespace WiFinderService
{
    // NOTE: You can use the "Rename" command on the "Refactor" menu to change the interface name "IPostErrors" in both code and config file together.
    [ServiceContract]
    public interface IPostData
    {
        [OperationContract]
        [WebInvoke(Method = "POST", UriTemplate = "v1/sensors/{ident_key}/errors",
          RequestFormat = WebMessageFormat.Json, ResponseFormat = WebMessageFormat.Json)]
        PostDataResponse PostErrors(string ident_key, Stream body);

        [OperationContract]
        [WebInvoke(Method = "POST", UriTemplate = "v1/sensors/{ident_key}",
          RequestFormat = WebMessageFormat.Json, ResponseFormat = WebMessageFormat.Json)]
        PostDataResponse PostLocations(string ident_key, Stream body);
    }
}
