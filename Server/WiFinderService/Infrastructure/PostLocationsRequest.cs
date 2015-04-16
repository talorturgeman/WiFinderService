using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Threading.Tasks;

namespace WiFinderService.Infrastructure
{
    class PostLocationsRequest
    {
        public string ident_key { get; set; }
        public IEnumerable<Device> data { get; set; }

        public class Device
        {
            public string mac;
            public string bssid;
            public string power;
            public string timestamp; //todo - convert to long
        };

        public bool UpdateDB()
        {
            return true;
        }

        public static string Parse(string body)
        {
            string stage3 = body.Substring(9);

            // todo: improve code
            stage3.Replace('-', '+');
            stage3.Replace('_', '/');
            stage3.Replace('.', '=');

            return Encoding.UTF8.GetString(Convert.FromBase64String(stage3));
        }

        static string DecryptStringFromBytes(byte[] cipherText, byte[] key, byte[] iv)
        {
            if (cipherText == null || cipherText.Length <= 0)
                throw new ArgumentNullException("cipherText");
            if (key == null || key.Length <= 0)
                throw new ArgumentNullException("key");

            string plainText;
            var rijndael = new RijndaelManaged()
            {
                Key = key,
                Mode = CipherMode.ECB,
                BlockSize = 256,
            };
            ICryptoTransform decryptor = rijndael.CreateDecryptor(rijndael.Key, rijndael.IV);

            using (var memoryStream = new MemoryStream(cipherText))
            {
                using (var cryptoStream = new CryptoStream(memoryStream, decryptor, CryptoStreamMode.Read))
                {
                    using (var streamReader = new StreamReader(cryptoStream))
                    {
                        plainText = streamReader.ReadToEnd();
                    }
                }
            }
            return plainText;
        }
    }
}
