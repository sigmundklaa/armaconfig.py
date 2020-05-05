#ifdef A
class C {
	f = 2;
};
#else
class A {
	x = 3;
};
#endif

#define a b
#define b a##b

class B {
	property = a;
};