import unittest                                                                                                                                                   
                                                                                                                                                                     
from streamlit.testing.v1 import AppTest                                                                                                                          
                                                                                                                                                                  
                                                                                                                                                                  
class AppSmokeTest(unittest.TestCase):                                                                                                                            
    def test_page_loads(self):                                                                                                                                    
        app = AppTest.from_file("app.py").run()                                                                                                                   
                                                                                                                                                                  
        self.assertEqual(len(app.exception), 0)                                                                                                                   
        self.assertEqual(app.title[0].value, "Docs Radar")                                                                                                        
        self.assertIn("Independent demo", app.caption[0].value)                                                                                                   
                                                                                                                                                                  
                                                                                                                                                                  
if __name__ == "__main__":                                                                                                                                        
    unittest.main()