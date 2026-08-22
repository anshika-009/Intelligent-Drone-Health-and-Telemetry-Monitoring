import '@testing-library/jest-dom/vitest';

class MockIntersectionObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
Object.defineProperty(window, 'IntersectionObserver', { writable: true, value: MockIntersectionObserver });
