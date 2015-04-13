using System;
using System.Collections.Generic;
using System.Linq;
using System.Runtime.Serialization;
using System.ServiceModel;
using System.ServiceModel.Web;
using System.Text;
using WiFinderServer.models;

namespace WiFinderService
{
    // NOTE: You can use the "Rename" command on the "Refactor" menu to change the class name "Service1" in both code and config file together.
    public class GetLocation : IGetLocation
    {
        [WebInvoke(Method = "GET",
            ResponseFormat = WebMessageFormat.Json,
            UriTemplate = "{mac}")]
        public PhoneLocation GetLocationByMac(string mac)
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
    /*
        public CompositeType GetDataUsingDataContract(CompositeType composite)
        {
            if (composite == null)
            {
                throw new ArgumentNullException("composite");
            }
            if (composite.BoolValue)
            {
                composite.StringValue += "Suffix";
            }
            return composite;
        }
    }*/
}
