import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit'
import { todosApi } from '../../services/api'

export interface Todo {
  id: string
  user_id: string
  title: string
  description?: string
  completed: boolean
  created_at: string
  updated_at: string
}

interface TodosState {
  todos: Todo[]
  loading: boolean
  error: string | null
}

const initialState: TodosState = {
  todos: [],
  loading: false,
  error: null,
}

// Async thunks
export const fetchTodos = createAsyncThunk('todos/fetchTodos', async () => {
  const response = await todosApi.getTodos()
  return response
})

export const createTodo = createAsyncThunk(
  'todos/createTodo',
  async ({ title, description }: { title: string; description?: string }) => {
    const response = await todosApi.createTodo(title, description)
    return response
  }
)

export const updateTodo = createAsyncThunk(
  'todos/updateTodo',
  async ({ id, title, description, completed }: Partial<Todo> & { id: string }) => {
    const response = await todosApi.updateTodo(id, { title, description, completed })
    return response
  }
)

export const deleteTodo = createAsyncThunk('todos/deleteTodo', async (id: string) => {
  await todosApi.deleteTodo(id)
  return id
})

const todosSlice = createSlice({
  name: 'todos',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch Todos
      .addCase(fetchTodos.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchTodos.fulfilled, (state, action) => {
        state.loading = false
        state.todos = action.payload
      })
      .addCase(fetchTodos.rejected, (state, action) => {
        state.loading = false
        state.error = action.error.message || 'Failed to fetch todos'
      })
      // Create Todo
      .addCase(createTodo.fulfilled, (state, action) => {
        state.todos.push(action.payload)
      })
      .addCase(createTodo.rejected, (state, action) => {
        state.error = action.error.message || 'Failed to create todo'
      })
      // Update Todo
      .addCase(updateTodo.fulfilled, (state, action) => {
        const index = state.todos.findIndex((todo) => todo.id === action.payload.id)
        if (index !== -1) {
          state.todos[index] = action.payload
        }
      })
      .addCase(updateTodo.rejected, (state, action) => {
        state.error = action.error.message || 'Failed to update todo'
      })
      // Delete Todo
      .addCase(deleteTodo.fulfilled, (state, action) => {
        state.todos = state.todos.filter((todo) => todo.id !== action.payload)
      })
      .addCase(deleteTodo.rejected, (state, action) => {
        state.error = action.error.message || 'Failed to delete todo'
      })
  },
})

export const { clearError } = todosSlice.actions
export default todosSlice.reducer

