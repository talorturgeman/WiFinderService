using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;

namespace WiFinderServer.models
{
    public class PhoneLocation
    {
        public string mac;
        public double x;
        public double y;
        public long timestamp;
        public double reability;
        public double radius;
    }
}