# coding: utf-8
# coding: utf-8
import editor
from objc_util import *
from objc_util import parse_types
import ctypes
import inspect
import sys

def _str_to_bytes(s):
	if sys.version_info[0] >= 3:
		if isinstance(s,bytes):
			return s
		else:
			return bytes(s,'ascii')
	else:
		return str(s)
@on_main_thread
def swizzle(cls, selector, new_fcn,type_encoding=None):
	'''swizzles ObjCClass cls's selector with implementation from python new_fcn.  new_fcn needs to adjere to ther type encoding of the original, including the two "hidden" arguments _self, _sel.

	if a class is already swizzled, this will override swizzled implemetation, and use new method.  We could implement a forwarding system, but it becomes hard to unswizzle because there is no way to remove a selector once added.  
	
	A method can always get its predecessor by simply prepending original to its selector name.
	
	If the referenced method does not exist, must supply type_encoding.
	
	'''

	if not type_encoding:				
		type_encoding=_str_to_bytes(str(cls.instanceMethodSignatureForSelector_(sel(selector))._typeString()))
	else:
		type_encoding=_str_to_bytes(type_encoding)
	parsed_types = parse_types(_str_to_bytes(type_encoding))
	restype = parsed_types[0]
	argtypes = parsed_types[1]
	# Check if the number of arguments derived from the selector matches the actual function:

	try:
		argspec=inspect.getargspec(new_fcn.__closure__[0].cell_contents)
	except:
		argspec = inspect.getargspec(new_fcn)
	if len(argspec.args) != len(argtypes):
		raise ValueError('%s has %i arguments (expected %i)' % (new_fcn, len(argspec.args), len(argtypes)))
	IMPTYPE = ctypes.CFUNCTYPE(restype, *argtypes)
	imp = IMPTYPE(new_fcn)
	retain_global(imp)
	
	#find rootmost parent
	# add new to orig_....   N (N-3) (N-2) (N-1)
	# then starting at end, swap up the chain
	if not c.class_getInstanceMethod(cls.ptr, sel(selector)):
		# just add the selector
		new_sel = selector
		didAdd=c.class_addMethod(cls.ptr, sel(new_sel), imp, (type_encoding))
		return
	
	new_sel = 'original'+selector
	didAdd=c.class_addMethod(cls.ptr, sel(new_sel), imp, (type_encoding))

	method_exchangeImplementations=c.method_exchangeImplementations
	method_exchangeImplementations.restype=None
	method_exchangeImplementations.argtypes=[c_void_p,c_void_p]
	
	method_setImplementation=c.method_setImplementation
	method_setImplementation.restype=None
	method_setImplementation.argtypes=[c_void_p, c_void_p]
	if didAdd:
			orig_method=c.class_getInstanceMethod(cls.ptr, sel(selector))
			new_method=c.class_getInstanceMethod(cls.ptr, sel(new_sel))
			method_exchangeImplementations(orig_method, new_method)
	else:
		# setimp, 
		orig_method=c.class_getInstanceMethod(cls.ptr, sel(selector))
		method_setImplementation(orig_method,imp)


if __name__=='__main__':
	import console
	t=editor._get_editor_tab()

	def saveData(_self,_sel):
		'''swizzle savedata. called whenever tab is switched, etc. seems to be called whether or not there are changes, so be sure to check if hasChanges before doing anything.  In this case, I always call _original_saveData after, but it would be possible to prevent saves, etc.'''
		try:
			obj=ObjCInstance(_self)
			if obj.hasChanges():
				console.hud_alert('saving '+str(obj.filePath()).split('/')[-1])
		finally:
			obj=ObjCInstance(_self)
			original_method=getattr(obj,'original'+c.sel_getName(_sel),None)
			if original_method:
				original_method()
			
	cls=ObjCInstance(c.object_getClass(t.ptr))
	swizzle(cls,'saveData',saveData)

											
											
