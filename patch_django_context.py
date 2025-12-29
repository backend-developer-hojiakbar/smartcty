"""
Patch for Django template context compatibility with Python 3.14
This addresses the issue where 'super' object has no attribute 'dicts' 
in the __copy__ method of Context class.
"""
import sys


# Apply the patch as soon as possible
if sys.version_info >= (3, 14):
    def apply_context_patch():
        try:
            from django.template.context import Context
            
            def patched_copy(self):
                """
                Patched __copy__ method that handles Python 3.14's object model changes
                """
                # Create a new instance of Context
                new_context = self.__class__(self.request)
                
                # Manually copy the dicts list
                new_context.dicts = []
                for d in self.dicts:
                    if hasattr(d, 'copy'):
                        new_context.dicts.append(d.copy())
                    else:
                        new_context.dicts.append(d)
                
                return new_context
            
            # Apply the patch
            Context.__copy__ = patched_copy
            print("Django Context patch applied successfully for Python 3.14+ compatibility")
            
        except ImportError:
            pass  # Django not loaded yet, will try again later
        except Exception as e:
            print(f"Could not apply Django Context patch: {e}")
    
    # Try to apply the patch immediately
    apply_context_patch()
    
    # Also patch the BaseContext if it exists
    try:
        from django.template.context import BaseContext
        
        def patched_base_copy(self):
            """
            Patched __copy__ method for BaseContext
            """
            # Create a new instance of the same class
            new_context = self.__class__(self.request)
            
            # Manually copy the dicts list
            new_context.dicts = []
            for d in self.dicts:
                if hasattr(d, 'copy'):
                    new_context.dicts.append(d.copy())
                else:
                    new_context.dicts.append(d)
            
            return new_context
        
        BaseContext.__copy__ = patched_base_copy
        print("Django BaseContext patch applied successfully for Python 3.14+ compatibility")
        
    except ImportError:
        pass  # BaseContext not available or not needed
    except Exception as e:
        print(f"Could not apply Django BaseContext patch: {e}")
else:
    print("Python version is below 3.14, no patch needed")