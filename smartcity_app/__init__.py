"""
Smart City App initialization
This file is executed when Django starts up.
"""

import sys

# Apply compatibility patch for Python 3.14+ and Django 4.2.7
if sys.version_info >= (3, 14):
    def apply_django_context_patches():
        """
        Patch Django template context classes for Python 3.14 compatibility.
        This fixes the AttributeError: 'RequestContext' object has no attribute '_processors_index'
        """
        try:
            from django.template.context import Context, RequestContext
            
            # Store original methods
            original_requestcontext_init = RequestContext.__init__
            original_requestcontext_bind_template = getattr(RequestContext, 'bind_template', None)
            
            def patched_requestcontext_init(self, *args, **kwargs):
                """Patched RequestContext.__init__ to ensure _processors_index is properly initialized"""
                # Call original __init__ with all arguments - this ensures compatibility with all Django versions
                original_requestcontext_init(self, *args, **kwargs)
                
                # CRITICAL FIX: Ensure _processors_index attribute exists
                # This attribute is required by bind_template but may not be set in Python 3.14
                if not hasattr(self, '_processors_index'):
                    # _processors_index indicates where processor dicts end in self.dicts
                    processor_count = 0
                    if hasattr(self, '_processors') and self._processors:
                        processor_count = len(self._processors)
                    
                    # Set the attribute using object.__setattr__ to avoid recursion
                    object.__setattr__(self, '_processors_index', processor_count)
            
            RequestContext.__init__ = patched_requestcontext_init
            
            # Patch bind_template method - this is where the error occurs
            if original_requestcontext_bind_template:
                def patched_bind_template(self, template):
                    """Patched bind_template to ensure _processors_index exists before accessing it"""
                    # Ensure _processors_index exists before calling original method
                    if not hasattr(self, '_processors_index'):
                        processor_count = 0
                        if hasattr(self, '_processors') and self._processors:
                            processor_count = len(self._processors)
                        object.__setattr__(self, '_processors_index', processor_count)
                    
                    # Now safely call the original method
                    return original_requestcontext_bind_template(self, template)
                
                RequestContext.bind_template = patched_bind_template
            
            # Patch RequestContext.__copy__ to handle _processors_index
            if hasattr(RequestContext, '__copy__'):
                original_copy = RequestContext.__copy__
                
                def patched_requestcontext_copy(self):
                    """Patched __copy__ method for RequestContext"""
                    # Create new instance using patched __init__
                    if hasattr(self, 'request'):
                        new_context = self.__class__(self.request)
                    else:
                        new_context = self.__class__(None)
                    
                    # Manually copy dicts
                    new_context.dicts = []
                    for d in self.dicts:
                        if hasattr(d, 'copy') and callable(getattr(d, 'copy')):
                            new_context.dicts.append(d.copy())
                        else:
                            new_context.dicts.append(d)
                    
                    # Copy other attributes
                    if hasattr(self, '_processors'):
                        new_context._processors = self._processors
                    if hasattr(self, '_current_app'):
                        new_context._current_app = self._current_app
                    if hasattr(self, '_renderer'):
                        new_context._renderer = self._renderer
                    
                    # Ensure _processors_index is copied
                    if hasattr(self, '_processors_index'):
                        object.__setattr__(new_context, '_processors_index', self._processors_index)
                    else:
                        processor_count = len(new_context._processors) if hasattr(new_context, '_processors') and new_context._processors else 0
                        object.__setattr__(new_context, '_processors_index', processor_count)
                    
                    return new_context
                
                RequestContext.__copy__ = patched_requestcontext_copy
            
            # Also patch Context.__copy__ for consistency
            if hasattr(Context, '__copy__'):
                original_context_copy = Context.__copy__
                
                def patched_context_copy(self):
                    """Patched __copy__ method for Context"""
                    if hasattr(self, 'request'):
                        new_context = self.__class__(self.request)
                    else:
                        new_context = self.__class__()
                    
                    new_context.dicts = []
                    for d in self.dicts:
                        if hasattr(d, 'copy') and callable(getattr(d, 'copy')):
                            new_context.dicts.append(d.copy())
                        else:
                            new_context.dicts.append(d)
                    
                    if hasattr(self, '_current_app'):
                        new_context._current_app = self._current_app
                    if hasattr(self, '_renderer'):
                        new_context._renderer = self._renderer
                    
                    return new_context
                
                Context.__copy__ = patched_context_copy
            
            print("[OK] Django RequestContext and Context patches applied for Python 3.14+ compatibility")
            
        except ImportError as e:
            print(f"[WARN] Import error while applying context patch: {e}")
            # Django might not be fully loaded yet, this is okay
            pass
        except Exception as e:
            print(f"[ERROR] Failed to apply Django context patch: {e}")
            import traceback
            traceback.print_exc()
    
    # Apply patches immediately when module is imported
    apply_django_context_patches()
else:
    print(f"Python {sys.version} does not require patch")
