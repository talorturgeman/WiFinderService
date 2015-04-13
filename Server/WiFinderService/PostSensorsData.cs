using System;
using System.Collections.Generic;
using System.Linq;
using System.ServiceModel;
using System.ServiceModel.Web;
using System.Text;
using System.Threading.Tasks;
using WiFinderServer.models;

namespace WiFinderService
{
    [ServiceContract]
    class PostSensorsData
    {
        [WebInvoke(Method = "POST",
            ResponseFormat = WebMessageFormat.Json,
            RequestFormat = WebMessageFormat.Json,
            UriTemplate = "data/v1/sensors/{ident_key}")]
        public PhoneLocation GetData(string mac)
        {
            if (mac == "00-15-E9-2B-99-3C")
            {
                return new PhoneLocation()
                {
                    mac = "00-15-E9-2B-99-3C",
                    radius = 0,
                    reability = 1,
                    timestamp = 500,
                    x = 1,
                    y = 1
                };
            }
            else
                return null;
        }
    }
}
