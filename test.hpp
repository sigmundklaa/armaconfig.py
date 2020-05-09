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
	array[] = {1, 2, 3, "4", 5 to 3};
};