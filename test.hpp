#ifdef A
class C {
	f = 2;
};
#else
class A {
	x = 3;
};
#endif

#define a(x) b(x)
#define b(n) a##b##n

class B {
	property = a(1);
};