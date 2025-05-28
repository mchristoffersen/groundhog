// Thread-safe locking queue
#pragma once
#include <condition_variable>
#include <iostream>
#include <mutex>
#include <queue>

// Thread-safe queue
template <typename T>
class tsQueue {
 private:
  std::queue<T> queue;
  std::mutex mtx;
  std::condition_variable cond;

 public:
  void push(T item) {
    std::scoped_lock lock{mtx};
    queue.push(item);
  }

  T pop() {
    std::unique_lock lock{mtx};

    cond.wait(lock, [this]() { return !queue.empty(); });

    T item = queue.front();
    queue.pop();

    return item;
  }

  size_t size() {
    std::scoped_lock lock{mtx};
    return queue.size();
  }

  bool empty() {
    std::scoped_lock lock{mtx};
    return queue.empty();
  }
};
