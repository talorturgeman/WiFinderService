using System;
using System.Collections.Generic;
using System.Collections.Specialized;
using System.IO;
using System.Linq;
using System.Runtime.Serialization;
using System.ServiceModel;
using System.Text;
using System.Web;
using System.Web.Script.Serialization;
using WiFinderService.Infrastructure;

namespace WiFinderService
{
    // NOTE: You can use the "Rename" command on the "Refactor" menu to change the class name "PostErrors" in both code and config file together.
    public class PostData : IPostData
    {
        public PostDataResponse PostErrors(string ident_key, Stream body)
        {
            StreamReader reader = new StreamReader(body);
            String res = reader.ReadToEnd();  

            JavaScriptSerializer serializer = new JavaScriptSerializer();
            ErrorsRequest collection = serializer.Deserialize<ErrorsRequest>(res);

            return new PostDataResponse(collection.UpdateDB());
        }

        public PostDataResponse PostLocations(string ident_key, Stream body)
        {
            StreamReader reader = new StreamReader(body);
            String res = reader.ReadToEnd();
            string json = PostLocationsRequest.Parse(res);

            JavaScriptSerializer serializer = new JavaScriptSerializer();
            PostLocationsRequest collection = serializer.Deserialize<PostLocationsRequest>(json);

            return new PostDataResponse(true);
        }
    }
}
