"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import Link from "next/link";
import {
  ChefHat,
  Eye,
  EyeOff,
  Mail,
  Lock,
  Sparkles,
  Loader,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

const loginSchema = z.object({
  email: z.string().email("Please enter a valid email address"),
  password: z.string().min(6, "Password must be at least 6 characters"),
  rememberMe: z.boolean(),
});

type LoginFormValues = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const [showPassword, setShowPassword] = useState(false);
  const router = useRouter();
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const form = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: "",
      password: "",
      rememberMe: false,
    },
  });

  const onSubmit = () => {
    setIsLoading(true);
    setTimeout(() => {
      setIsLoading(false);
      toast.success("Login Successful");
      router.push("/dashboard");
    }, 1000);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-white dark:bg-black light:bg-white p-4 transition-colors">
      <div className="w-full max-w-md space-y-8">
        {/* Logo and Header */}
        <div className="text-center space-y-4">
          <div className="flex justify-center">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-purple-600 to-blue-600 flex items-center justify-center shadow-lg">
              <ChefHat className="w-8 h-8 text-white" />
            </div>
          </div>
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent">
              Hospitality AI
            </h1>
            <p className="text-gray-500 dark:text-gray-400 text-sm mt-1">
              Enterprise Restaurant Intelligence
            </p>
          </div>
        </div>

        {/* Login Card */}
        <div
          className="
          bg-gray-900/50 dark:bg-gray-900/50 
          bg-white/70 light:bg-white 
          backdrop-blur-sm 
          border border-gray-800 dark:border-gray-800 
          light:border-gray-200 
          rounded-2xl p-8 space-y-6 
          shadow-2xl
        "
        >
          <div className="space-y-2">
            <h2 className="text-2xl font-semibold text-black dark:text-white light:text-gray-900">
              Welcome back
            </h2>
            <p className="text-gray-500 dark:text-gray-400 light:text-gray-600 text-sm">
              Sign in to access your restaurant analytics
            </p>
          </div>

          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              {/* Email Field */}
              <FormField
                control={form.control}
                name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-gray-500 dark:text-gray-300 light:text-gray-700 text-sm">
                      Email Address
                    </FormLabel>
                    <FormControl>
                      <div className="relative">
                        <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                        <Input
                          {...field}
                          type="email"
                          placeholder="you@restaurant.com"
                          className="
                            pl-10 
                            bg-gray-800/50 dark:bg-gray-800/50 
                            light:bg-gray-100 light:border-gray-300
                            border-gray-700 dark:border-gray-700 
                            text-white dark:text-white light:text-gray-900 
                            placeholder:text-gray-500 
                            focus-visible:ring-purple-500 focus-visible:ring-offset-0
                            focus-visible:border-purple-500
                          "
                        />
                      </div>
                    </FormControl>
                    <FormMessage className="text-red-400 light:text-red-500" />
                  </FormItem>
                )}
              />

              {/* Password Field */}
              <FormField
                control={form.control}
                name="password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-gray-500 dark:text-gray-300 light:text-gray-700 text-sm">
                      Password
                    </FormLabel>
                    <FormControl>
                      <div className="relative">
                        <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                        <Input
                          {...field}
                          type={showPassword ? "text" : "password"}
                          placeholder="Enter your password"
                          className="
                            pl-10 pr-10 
                            bg-gray-800/50 dark:bg-gray-800/50 
                            light:bg-gray-100 light:border-gray-300
                            border-gray-700 dark:border-gray-700 
                            text-white dark:text-white light:text-gray-900 
                            placeholder:text-gray-500 
                            focus-visible:ring-purple-500 focus-visible:ring-offset-0
                            focus-visible:border-purple-500
                          "
                        />
                        <button
                          type="button"
                          onClick={() => setShowPassword(!showPassword)}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300 dark:hover:text-gray-300 light:hover:text-gray-600 transition-colors"
                        >
                          {showPassword ? (
                            <EyeOff className="w-5 h-5" />
                          ) : (
                            <Eye className="w-5 h-5" />
                          )}
                        </button>
                      </div>
                    </FormControl>
                    <FormMessage className="text-red-400 light:text-red-500" />
                  </FormItem>
                )}
              />

              {/* Remember Me & Forgot Password */}
              <div className="flex items-center justify-between">
                <FormField
                  control={form.control}
                  name="rememberMe"
                  render={({ field }) => (
                    <FormItem className="flex items-center space-x-2 space-y-0">
                      <FormControl>
                        <Checkbox
                          checked={field.value}
                          onCheckedChange={field.onChange}
                          className="
                            border-gray-600 
                            data-[state=checked]:bg-purple-600 
                            data-[state=checked]:border-purple-600
                            light:border-gray-400 
                            light:data-[state=checked]:bg-purple-600
                          "
                        />
                      </FormControl>
                      <FormLabel className="text-sm text-gray-400 dark:text-gray-400 light:text-gray-600 font-normal cursor-pointer">
                        Remember me
                      </FormLabel>
                    </FormItem>
                  )}
                />
                <Link
                  href="/auth/forgot-password"
                  className="text-sm text-purple-400 hover:text-purple-300 light:text-purple-600 light:hover:text-purple-500 transition-colors"
                >
                  Forgot password?
                </Link>
              </div>

              {/* Submit Button */}
              <Button
                disabled={isLoading}
                type="submit"
                className="
                  w-full bg-gradient-to-r from-purple-600 to-blue-600 
                  hover:from-purple-700 hover:to-blue-700 
                  text-white font-medium py-6 rounded-xl 
                  shadow-lg hover:shadow-purple-500/25
                  transition-all duration-200
                "
              >
                {isLoading ? (
                  <span className="flex items-center">
                    Signing In...{" "}
                    <Loader className="w-4 h-4 ml-2 animate-spin" />
                  </span>
                ) : (
                  <span className="flex items-center">
                    Sign in
                    <Sparkles className="w-4 h-4 ml-2" />
                  </span>
                )}
              </Button>
            </form>
          </Form>
        </div>

        {/* Optional: Footer */}
        <p className="text-center text-xs text-gray-500 dark:text-gray-500 light:text-gray-600">
          © 2025 Hospitality AI. All rights reserved.
        </p>
      </div>
    </div>
  );
}
