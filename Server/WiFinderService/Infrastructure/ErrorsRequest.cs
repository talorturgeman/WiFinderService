using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace WiFinderService.Infrastructure
{
    class ErrorsRequest
    {
        public string ident_key { get; set; }
        public IEnumerable<Error> data { get; set; }

        public class Error
        {
            public int errorLevel;
            public string module;
            public string message;
        };

        public bool UpdateDB()
        {
            return true;
        }
    }
}
